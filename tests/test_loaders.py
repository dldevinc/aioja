import os

import pytest

from aioja.environment import Environment
from aioja.loaders import (
    ChoiceLoader,
    DictLoader,
    FileSystemLoader,
    FunctionLoader,
    ModuleLoader,
    PackageLoader,
    PrefixLoader,
)


@pytest.mark.asyncio
async def test_filesystem_loader():
    env = Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        loader=FileSystemLoader("tests/templates")
    )

    template = await env.get_template("list.html")
    content = template.render(array=["Red", "Blue", "Green"])
    assert content == (
        "<ul>\n"
        "    <li>Red</li>\n"
        "    <li>Blue</li>\n"
        "    <li>Green</li>\n"
        "</ul>"
    )


@pytest.mark.asyncio
async def test_filesystem_loader_templates():
    env = Environment(
        loader=FileSystemLoader("tests/templates")
    )

    templates = await env.list_templates()
    assert set(templates) == {
        "list.html",
        "text.html",
    }


@pytest.mark.asyncio
async def test_module_loader():
    env = Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        loader=ChoiceLoader([
            ModuleLoader("tests/compiled"),
            FileSystemLoader("tests/templates"),
        ])
    )

    # precompile templates
    await env.compile_templates(
        "tests/compiled",
        zip=None
    )

    assert os.path.isfile("tests/compiled/tmpl_7cf55666eecc765859bfbe8a10c163548abcbbf9.py")
    assert os.path.isfile("tests/compiled/tmpl_24bbb006a6564ab6d1f32e3604e76401b4b8dd93.py")

    template = await env.get_template("list.html")
    assert template is not None

    content = template.render(array=["One", "Two", "Three"])
    assert content == (
        "<ul>\n"
        "    <li>One</li>\n"
        "    <li>Two</li>\n"
        "    <li>Three</li>\n"
        "</ul>"
    )


@pytest.mark.asyncio
async def test_module_loader_templates():
    env = Environment(
        loader=ModuleLoader("tests/compiled")
    )

    templates = await env.list_templates()
    assert set(templates) == set()


@pytest.mark.asyncio
async def test_package_loader():
    env = Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        loader=PackageLoader("tests")
    )

    template = await env.get_template("list.html")
    content = template.render(array=["1", "2", "3", "4"])
    assert content == (
        "<ul>\n"
        "    <li>1</li>\n"
        "    <li>2</li>\n"
        "    <li>3</li>\n"
        "    <li>4</li>\n"
        "</ul>"
    )


@pytest.mark.asyncio
async def test_package_loader_templates():
    env = Environment(
        loader=PackageLoader("tests")
    )

    templates = await env.list_templates()
    assert set(templates) == {
        "list.html",
        "text.html"
    }


@pytest.mark.asyncio
async def test_dict_loader():
    env = Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        loader=DictLoader({
            "var": "<div>{{ value }}</div>"
        })
    )

    template = await env.get_template("var")
    content = template.render(value="Hello")
    assert content == "<div>Hello</div>"


@pytest.mark.asyncio
async def test_dict_loader_templates():
    env = Environment(
        loader=DictLoader({
            "var": "<div>{{ value }}</div>"
        })
    )

    templates = await env.list_templates()
    assert set(templates) == {
        "var"
    }


@pytest.mark.asyncio
async def test_function_loader():
    async def get_source(name):
        return "<{0}>{{{{ value }}}}</{0}>".format(name)

    env = Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        loader=FunctionLoader(get_source)
    )

    template = await env.get_template("span")
    content = template.render(value="Silver")
    assert content == "<span>Silver</span>"


@pytest.mark.asyncio
async def test_function_loader_templates():
    async def get_source(name):
        return "<{0}>{{{{ value }}}}</{0}>".format(name)

    env = Environment(
        loader=FunctionLoader(get_source)
    )

    templates = await env.list_templates()
    assert set(templates) == set()


@pytest.mark.asyncio
async def test_prefix_loader():
    async def get_source(name):
        return "<{0}>{{{{ value }}}}</{0}>".format(name)

    env = Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        loader=PrefixLoader({
            "func": FunctionLoader(get_source),
            "dict": DictLoader({
                "header": "<h2>{{ title }}</h2>"
            }),
        })
    )

    template = await env.get_template("func/article")
    content = template.render(value="Paragraph")
    assert content == "<article>Paragraph</article>"

    template = await env.get_template("dict/header")
    content = template.render(title="Header")
    assert content == "<h2>Header</h2>"


@pytest.mark.asyncio
async def test_prefix_loader_templates():
    async def get_source(name):
        return '<{0}>{{{{ value }}}}</{0}>'.format(name)

    env = Environment(
        loader=PrefixLoader({
            "func": FunctionLoader(get_source),
            "dict": DictLoader({
                "header": "<h2>{{ title }}</h2>"
            }),
        })
    )

    templates = await env.list_templates()
    assert set(templates) == {
        "dict/header"
    }
