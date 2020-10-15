import sys
from os import path

from jinja2 import loaders
from jinja2._compat import string_types, iteritems
from jinja2.exceptions import TemplateNotFound
from jinja2.utils import internalcode

from .utils import open_if_exists


class AsyncLoaderMixin:
    @internalcode
    async def load(self, environment, name, globals=None):
        """Loads a template.  This method looks up the template in the cache
        or loads one by calling :meth:`get_source`.  Subclasses should not
        override this method as loaders working on collections of other
        loaders (such as :class:`PrefixLoader` or :class:`ChoiceLoader`)
        will not call this method but `get_source` directly.
        """
        code = None
        if globals is None:
            globals = {}

        # first we try to get the source for this template together
        # with the filename and the uptodate function.
        source, filename, uptodate = await self.get_source(environment, name)

        # try to load the code from the bytecode cache if there is a
        # bytecode cache configured.
        bcc = environment.bytecode_cache
        if bcc is not None:
            bucket = await bcc.get_bucket(environment, name, filename, source)
            code = bucket.code

        # if we don't have code so far (not cached, no longer up to
        # date) etc. we compile the template
        if code is None:
            code = environment.compile(source, name, filename)

        # if the bytecode cache is available and the bucket doesn't
        # have a code so far, we give the bucket the new code and put
        # it back to the bytecode cache.
        if bcc is not None and bucket.code is None:
            bucket.code = code
            await bcc.set_bucket(bucket)

        return environment.template_class.from_code(
            environment, code, globals, uptodate
        )


class FileSystemLoader(AsyncLoaderMixin, loaders.FileSystemLoader):
    async def get_source(self, environment, template):
        pieces = loaders.split_template_path(template)
        for searchpath in self.searchpath:
            filename = path.join(searchpath, *pieces)
            f = await open_if_exists(filename)
            if f is None:
                continue
            try:
                contents = await f.read()
            finally:
                await f.close()

            contents = contents.decode(self.encoding)
            mtime = path.getmtime(filename)

            def uptodate():
                try:
                    return path.getmtime(filename) == mtime
                except OSError:
                    return False

            return contents, filename, uptodate
        raise TemplateNotFound(template)

    async def list_templates(self):
        return super().list_templates()


class PackageLoader(AsyncLoaderMixin, loaders.PackageLoader):
    async def get_source(self, environment, template):
        return super().get_source(environment, template)

    async def list_templates(self):
        return super().list_templates()


class DictLoader(AsyncLoaderMixin, loaders.DictLoader):
    async def get_source(self, environment, template):
        return super().get_source(environment, template)

    async def list_templates(self):
        return super().list_templates()


class FunctionLoader(AsyncLoaderMixin, loaders.FunctionLoader):
    async def get_source(self, environment, template):
        rv = await self.load_func(template)
        if rv is None:
            raise TemplateNotFound(template)
        elif isinstance(rv, string_types):
            return rv, None, None
        return rv

    async def list_templates(self):
        # FIX: jinja2 bug
        return []


class PrefixLoader(AsyncLoaderMixin, loaders.PrefixLoader):
    async def get_source(self, environment, template):
        loader, name = self.get_loader(template)
        try:
            return await loader.get_source(environment, name)
        except TemplateNotFound:
            # re-raise the exception with the correct filename here.
            # (the one that includes the prefix)
            raise TemplateNotFound(template)

    @internalcode
    async def load(self, environment, name, globals=None):
        loader, local_name = self.get_loader(name)
        try:
            return await loader.load(environment, local_name, globals)
        except TemplateNotFound:
            # re-raise the exception with the correct filename here.
            # (the one that includes the prefix)
            raise TemplateNotFound(name)

    async def list_templates(self):
        result = []
        for prefix, loader in iteritems(self.mapping):
            for template in await loader.list_templates():
                result.append(prefix + self.delimiter + template)
        return result


class ChoiceLoader(AsyncLoaderMixin, loaders.ChoiceLoader):
    async def get_source(self, environment, template):
        for loader in self.loaders:
            if loader.has_source_access:  # FIX: jinja2 bug
                try:
                    return await loader.get_source(environment, template)
                except TemplateNotFound:
                    pass
        raise TemplateNotFound(template)

    @internalcode
    async def load(self, environment, name, globals=None):
        for loader in self.loaders:
            try:
                return await loader.load(environment, name, globals)
            except TemplateNotFound:
                pass
        raise TemplateNotFound(name)

    async def list_templates(self):
        found = set()
        for loader in self.loaders:
            found.update(await loader.list_templates())
        return sorted(found)


class ModuleLoader(AsyncLoaderMixin, loaders.ModuleLoader):
    @internalcode
    async def load(self, environment, name, globals=None):
        key = self.get_template_key(name)
        module = "%s.%s" % (self.package_name, key)
        mod = getattr(self.module, module, None)
        if mod is None:
            try:
                mod = __import__(module, None, None, ["root"])
            except ImportError:
                raise TemplateNotFound(name)

            # remove the entry from sys.modules, we only want the attribute
            # on the module object we have stored on the loader.
            sys.modules.pop(module, None)

        return environment.template_class.from_module_dict(
            environment, mod.__dict__, globals
        )

    async def list_templates(self):
        # FIX: jinja2 bug
        return []
