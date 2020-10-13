import os
import sys
import weakref

import aiofiles
from jinja2._compat import PY2, PYPY, encode_filename, string_types, text_type
from jinja2.environment import Environment as DefaultEnvironment, Template
from jinja2.exceptions import (
    TemplateNotFound,
    TemplatesNotFound,
    TemplateSyntaxError,
    UndefinedError,
)
from jinja2.runtime import Undefined
from jinja2.utils import internalcode


class Environment(DefaultEnvironment):
    def __init__(self, *args, **kwargs):
        kwargs['enable_async'] = True
        super().__init__(*args, **kwargs)

    @internalcode
    async def _load_template(self, name, globals):
        if self.loader is None:
            raise TypeError("no loader for this environment specified")
        cache_key = (weakref.ref(self.loader), name)
        if self.cache is not None:
            template = self.cache.get(cache_key)
            if template is not None and (
                not self.auto_reload or template.is_up_to_date
            ):
                return template
        template = await self.loader.load(self, name, globals)
        if self.cache is not None:
            self.cache[cache_key] = template
        return template

    @internalcode
    async def get_template(self, name, parent=None, globals=None):
        """Load a template from the loader.  If a loader is configured this
        method asks the loader for the template and returns a :class:`Template`.
        If the `parent` parameter is not `None`, :meth:`join_path` is called
        to get the real template name before loading.

        The `globals` parameter can be used to provide template wide globals.
        These variables are available in the context at render time.

        If the template does not exist a :exc:`TemplateNotFound` exception is
        raised.

        .. versionchanged:: 2.4
           If `name` is a :class:`Template` object it is returned from the
           function unchanged.
        """
        if isinstance(name, Template):
            return name
        if parent is not None:
            name = self.join_path(name, parent)
        return await self._load_template(name, self.make_globals(globals))

    @internalcode
    async def select_template(self, names, parent=None, globals=None):
        """Works like :meth:`get_template` but tries a number of templates
        before it fails.  If it cannot find any of the templates, it will
        raise a :exc:`TemplatesNotFound` exception.

        .. versionchanged:: 2.11
            If names is :class:`Undefined`, an :exc:`UndefinedError` is
            raised instead. If no templates were found and names
            contains :class:`Undefined`, the message is more helpful.

        .. versionchanged:: 2.4
           If `names` contains a :class:`Template` object it is returned
           from the function unchanged.

        .. versionadded:: 2.3
        """
        if isinstance(names, Undefined):
            names._fail_with_undefined_error()

        if not names:
            raise TemplatesNotFound(
                message="Tried to select from an empty list of templates."
            )
        globals = self.make_globals(globals)
        for name in names:
            if isinstance(name, Template):
                return name
            if parent is not None:
                name = self.join_path(name, parent)
            try:
                return await self._load_template(name, globals)
            except (TemplateNotFound, UndefinedError):
                pass
        raise TemplatesNotFound(names)

    @internalcode
    async def get_or_select_template(self, template_name_or_list, parent=None, globals=None):
        """Does a typecheck and dispatches to :meth:`select_template`
        if an iterable of template names is given, otherwise to
        :meth:`get_template`.

        .. versionadded:: 2.3
        """
        if isinstance(template_name_or_list, (string_types, Undefined)):
            return await self.get_template(template_name_or_list, parent, globals)
        elif isinstance(template_name_or_list, Template):
            return template_name_or_list
        return await self.select_template(template_name_or_list, parent, globals)

    async def compile_templates(
        self,
        target,
        extensions=None,
        filter_func=None,
        zip="deflated",
        log_function=None,
        ignore_errors=True,
        py_compile=False,
    ):
        """Finds all the templates the loader can find, compiles them
        and stores them in `target`.  If `zip` is `None`, instead of in a
        zipfile, the templates will be stored in a directory.
        By default a deflate zip algorithm is used. To switch to
        the stored algorithm, `zip` can be set to ``'stored'``.

        `extensions` and `filter_func` are passed to :meth:`list_templates`.
        Each template returned will be compiled to the target folder or
        zipfile.

        By default template compilation errors are ignored.  In case a
        log function is provided, errors are logged.  If you want template
        syntax errors to abort the compilation you can set `ignore_errors`
        to `False` and you will get an exception on syntax errors.

        If `py_compile` is set to `True` .pyc files will be written to the
        target instead of standard .py files.  This flag does not do anything
        on pypy and Python 3 where pyc files are not picked up by itself and
        don't give much benefit.

        .. versionadded:: 2.4
        """
        from .loaders import ModuleLoader

        if log_function is None:

            def log_function(x):
                pass

        if py_compile:
            if not PY2 or PYPY:
                import warnings

                warnings.warn(
                    "'py_compile=True' has no effect on PyPy or Python"
                    " 3 and will be removed in version 3.0",
                    DeprecationWarning,
                    stacklevel=2,
                )
                py_compile = False
            else:
                import imp
                import marshal

                py_header = imp.get_magic() + u"\xff\xff\xff\xff".encode("iso-8859-15")

                # Python 3.3 added a source filesize to the header
                if sys.version_info >= (3, 3):
                    py_header += u"\x00\x00\x00\x00".encode("iso-8859-15")

        async def write_file(filename, data):
            if zip:
                info = ZipInfo(filename)
                info.external_attr = 0o755 << 16
                zip_file.writestr(info, data)
            else:
                if isinstance(data, text_type):
                    data = data.encode("utf8")

                async with aiofiles.open(os.path.join(target, filename), "wb") as f:
                    await f.write(data)

        if zip is not None:
            from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

            zip_file = ZipFile(
                target, "w", dict(deflated=ZIP_DEFLATED, stored=ZIP_STORED)[zip]
            )
            log_function('Compiling into Zip archive "%s"' % target)
        else:
            if not os.path.isdir(target):
                os.makedirs(target)
            log_function('Compiling into folder "%s"' % target)

        try:
            for name in self.list_templates(extensions, filter_func):
                source, filename, _ = await self.loader.get_source(self, name)
                try:
                    code = self.compile(source, name, filename, True, True)
                except TemplateSyntaxError as e:
                    if not ignore_errors:
                        raise
                    log_function('Could not compile "%s": %s' % (name, e))
                    continue

                filename = ModuleLoader.get_module_filename(name)

                if py_compile:
                    c = self._compile(code, encode_filename(filename))
                    await write_file(filename + "c", py_header + marshal.dumps(c))
                    log_function('Byte-compiled "%s" as %s' % (name, filename + "c"))
                else:
                    await write_file(filename, code)
                    log_function('Compiled "%s" as %s' % (name, filename))
        finally:
            if zip is not None:
                zip_file.close()

        log_function("Finished compiling templates")
