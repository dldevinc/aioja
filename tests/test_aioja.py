import os
import shutil

import pytest

from aioja.bccache import AsyncFileSystemBytecodeCache
from aioja.environment import Environment
from aioja.loaders import FileSystemLoader


class TestEnvironment:
    def setup_class(self):
        self.env = Environment(
            enable_async=True,
            trim_blocks=True,
            lstrip_blocks=True,
            loader=FileSystemLoader('tests/templates')
        )

    @pytest.mark.asyncio
    async def test_get_template(self):
        template = await self.env.get_template('text.html')
        assert template is not None

    @pytest.mark.asyncio
    async def test_select_template(self):
        template = await self.env.select_template(['missing.html', 'text.html'])
        assert template is not None

    @pytest.mark.asyncio
    async def test_get_or_select_template(self):
        template1 = await self.env.get_or_select_template('text.html')
        template2 = await self.env.get_or_select_template(['missing.html', 'text.html'])
        assert template1 is not None
        assert template2 is not None

    @pytest.mark.asyncio
    async def test_rendering(self):
        template = await self.env.get_template('text.html')
        content = await template.render_async(title='Page Title', text='Great freedom :-)')
        assert content == (
            '<h1>Page Title</h1>\n'
            '<p>Great freedom :-)</p>'
        )


@pytest.mark.asyncio
async def test_async_file_bytecode_cache():
    env = Environment(
        enable_async=True,
        trim_blocks=True,
        lstrip_blocks=True,
        loader=FileSystemLoader('tests/templates'),
        bytecode_cache=AsyncFileSystemBytecodeCache('tests/jinja_cache', '%s.cache')
    )

    bucket_key = '3d566c27c1dca9e2cf7cf410ce798d0fe23bb149'

    # clean bytecode cache
    shutil.rmtree('tests/jinja_cache', ignore_errors=True)
    os.makedirs('tests/jinja_cache')

    # first load - from file
    file_template = await env.get_template('list.html')
    assert file_template is not None
    assert os.path.isfile('tests/jinja_cache/%s.cache' % bucket_key)

    # clean env cache
    env.cache.clear()

    # second load - from bytecode cache
    template = await env.get_template('list.html')
    assert template is not None

    content = await template.render_async(array=['One', 'Two', 'Three'])
    assert content == (
        '<ul>\n'
        '    <li>One</li>\n'
        '    <li>Two</li>\n'
        '    <li>Three</li>\n'
        '</ul>'
    )
