import os
import shutil

import pytest

from aioja.bccache import AsyncFileSystemBytecodeCache
from aioja.environment import Environment
from aioja.loaders import ChoiceLoader, FileSystemLoader, ModuleLoader


class TestEnvironment:
    def setup_class(self):
        self.env = Environment(
            trim_blocks=True,
            lstrip_blocks=True,
            loader=FileSystemLoader('tests/templates')
        )

    @pytest.mark.asyncio
    async def test_get_template(self):
        template = await self.env.get_template('example.html')
        assert template is not None

    @pytest.mark.asyncio
    async def test_select_template(self):
        template = await self.env.select_template(['missing.html', 'example.html'])
        assert template is not None

    @pytest.mark.asyncio
    async def test_get_or_select_template(self):
        template1 = await self.env.get_or_select_template('example.html')
        template2 = await self.env.get_or_select_template(['missing.html', 'example.html'])
        assert template1 is not None
        assert template2 is not None

    @pytest.mark.asyncio
    async def test_rendering(self):
        template = await self.env.get_template('example.html')
        content = await template.render_async(array=['One', 'Two', 'Three'])
        assert content == (
            '<ul>\n'
            '    <li>One</li>\n'
            '    <li>Two</li>\n'
            '    <li>Three</li>\n'
            '</ul>'
        )


@pytest.mark.asyncio
async def test_async_file_bytecode_cache():
    env = Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        loader=FileSystemLoader('tests/templates'),
        bytecode_cache=AsyncFileSystemBytecodeCache('tests/jinja_cache', '%s.cache')
    )

    bucket_key = '0d5e391ad86ee505e39df96fbcb5c9822224798f'

    # clean bytecode cache
    shutil.rmtree('tests/jinja_cache', ignore_errors=True)
    os.makedirs('tests/jinja_cache')

    # first load - from file
    file_template = await env.get_template('example.html')
    assert file_template is not None
    assert os.path.isfile('tests/jinja_cache/%s.cache' % bucket_key)

    # clean env cache
    env.cache.clear()

    # second load - from bytecode cache
    template = await env.get_template('example.html')
    assert template is not None

    content = await template.render_async(array=['One', 'Two', 'Three'])
    assert content == (
        '<ul>\n'
        '    <li>One</li>\n'
        '    <li>Two</li>\n'
        '    <li>Three</li>\n'
        '</ul>'
    )


@pytest.mark.asyncio
async def test_compile_templates():
    env = Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        loader=ChoiceLoader([
            ModuleLoader('tests/compiled'),
            FileSystemLoader('tests/templates'),
        ])
    )

    # precompile templates
    await env.compile_templates(
        'tests/compiled',
        zip=None
    )

    assert os.path.isfile('tests/compiled/tmpl_15b077f129e7c6eb4bf99ed88e9c8ead954d6dcd.py')

    template = await env.get_template('example.html')
    assert template is not None

    content = await template.render_async(array=['One', 'Two', 'Three'])
    assert content == (
        '<ul>\n'
        '    <li>One</li>\n'
        '    <li>Two</li>\n'
        '    <li>Three</li>\n'
        '</ul>'
    )
