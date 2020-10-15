from jinja2 import nodes
from jinja2._compat import string_types, imap
from jinja2.compiler import (
    CodeGenerator,
    CompilerExit,
    dict_item_iter,
    supports_yield_from,
)


class AsyncCodeGenerator(CodeGenerator):
    """
    FIX: replaced `get_template()` with `await get_template()`.
    """

    def visit_Extends(self, node, frame):
        """Calls the extender."""
        if not frame.toplevel:
            self.fail("cannot use extend from a non top-level scope", node.lineno)

        # if the number of extends statements in general is zero so
        # far, we don't have to add a check if something extended
        # the template before this one.
        if self.extends_so_far > 0:

            # if we have a known extends we just add a template runtime
            # error into the generated code.  We could catch that at compile
            # time too, but i welcome it not to confuse users by throwing the
            # same error at different times just "because we can".
            if not self.has_known_extends:
                self.writeline("if parent_template is not None:")
                self.indent()
            self.writeline("raise TemplateRuntimeError(%r)" % "extended multiple times")

            # if we have a known extends already we don't need that code here
            # as we know that the template execution will end here.
            if self.has_known_extends:
                raise CompilerExit()
            else:
                self.outdent()

        self.writeline("parent_template = await environment.get_template(", node)
        self.visit(node.template, frame)
        self.write(", %r)" % self.name)
        self.writeline(
            "for name, parent_block in parent_template.blocks.%s():" % dict_item_iter
        )
        self.indent()
        self.writeline("context.blocks.setdefault(name, []).append(parent_block)")
        self.outdent()

        # if this extends statement was in the root level we can take
        # advantage of that information and simplify the generated code
        # in the top level from this point onwards
        if frame.rootlevel:
            self.has_known_extends = True

        # and now we have one more
        self.extends_so_far += 1

    def visit_Include(self, node, frame):
        """Handles includes."""
        if node.ignore_missing:
            self.writeline("try:")
            self.indent()

        func_name = "get_or_select_template"
        if isinstance(node.template, nodes.Const):
            if isinstance(node.template.value, string_types):
                func_name = "get_template"
            elif isinstance(node.template.value, (tuple, list)):
                func_name = "select_template"
        elif isinstance(node.template, (nodes.Tuple, nodes.List)):
            func_name = "select_template"

        self.writeline("template = await environment.%s(" % func_name, node)
        self.visit(node.template, frame)
        self.write(", %r)" % self.name)
        if node.ignore_missing:
            self.outdent()
            self.writeline("except TemplateNotFound:")
            self.indent()
            self.writeline("pass")
            self.outdent()
            self.writeline("else:")
            self.indent()

        skip_event_yield = False
        if node.with_context:
            loop = self.environment.is_async and "async for" or "for"
            self.writeline(
                "%s event in template.root_render_func("
                "template.new_context(context.get_all(), True, "
                "%s)):" % (loop, self.dump_local_context(frame))
            )
        elif self.environment.is_async:
            self.writeline(
                "for event in (await "
                "template._get_default_module_async())"
                "._body_stream:"
            )
        else:
            if supports_yield_from:
                self.writeline("yield from template._get_default_module()._body_stream")
                skip_event_yield = True
            else:
                self.writeline(
                    "for event in template._get_default_module()._body_stream:"
                )

        if not skip_event_yield:
            self.indent()
            self.simple_write("event", frame)
            self.outdent()

        if node.ignore_missing:
            self.outdent()

    def visit_Import(self, node, frame):
        """
        FIX:
        Double `await` for "environment.get_template()._get_default_module_async()"
        """
        self.writeline("%s = " % frame.symbols.ref(node.target), node)
        if frame.toplevel:
            self.write("context.vars[%r] = " % node.target)
        if self.environment.is_async:
            self.write("await (await environment.get_template(")
            self.visit(node.template, frame)
            self.write(", %r))." % self.name)
        else:
            self.write("environment.get_template(")
            self.visit(node.template, frame)
            self.write(", %r)." % self.name)
        if node.with_context:
            self.write(
                "make_module%s(context.get_all(), True, %s)"
                % (
                    self.environment.is_async and "_async" or "",
                    self.dump_local_context(frame),
                )
            )
        elif self.environment.is_async:
            self.write("_get_default_module_async()")
        else:
            self.write("_get_default_module()")
        if frame.toplevel and not node.target.startswith("_"):
            self.writeline("context.exported_vars.discard(%r)" % node.target)

    def visit_FromImport(self, node, frame):
        """
        FIX:
        Double `await` for "environment.get_template()._get_default_module_async()"
        """
        self.newline(node)

        if self.environment.is_async:
            self.write("included_template = await (await environment.get_template(")
            self.visit(node.template, frame)
            self.write(", %r))." % self.name)
        else:
            self.write("included_template = environment.get_template(")
            self.visit(node.template, frame)
            self.write(", %r)." % self.name)

        if node.with_context:
            self.write(
                "make_module%s(context.get_all(), True, %s)"
                % (
                    self.environment.is_async and "_async" or "",
                    self.dump_local_context(frame),
                )
            )
        elif self.environment.is_async:
            self.write("_get_default_module_async()")
        else:
            self.write("_get_default_module()")

        var_names = []
        discarded_names = []
        for name in node.names:
            if isinstance(name, tuple):
                name, alias = name
            else:
                alias = name
            self.writeline(
                "%s = getattr(included_template, "
                "%r, missing)" % (frame.symbols.ref(alias), name)
            )
            self.writeline("if %s is missing:" % frame.symbols.ref(alias))
            self.indent()
            self.writeline(
                "%s = undefined(%r %% "
                "included_template.__name__, "
                "name=%r)"
                % (
                    frame.symbols.ref(alias),
                    "the template %%r (imported on %s) does "
                    "not export the requested name %s"
                    % (self.position(node), repr(name)),
                    name,
                )
            )
            self.outdent()
            if frame.toplevel:
                var_names.append(alias)
                if not alias.startswith("_"):
                    discarded_names.append(alias)

        if var_names:
            if len(var_names) == 1:
                name = var_names[0]
                self.writeline(
                    "context.vars[%r] = %s" % (name, frame.symbols.ref(name))
                )
            else:
                self.writeline(
                    "context.vars.update({%s})"
                    % ", ".join(
                        "%r: %s" % (name, frame.symbols.ref(name)) for name in var_names
                    )
                )
        if discarded_names:
            if len(discarded_names) == 1:
                self.writeline("context.exported_vars.discard(%r)" % discarded_names[0])
            else:
                self.writeline(
                    "context.exported_vars.difference_"
                    "update((%s))" % ", ".join(imap(repr, discarded_names))
                )
