import pytest
from aioja.utils import open_if_exists


@pytest.mark.asyncio
async def test_file_not_found():
    fp = await open_if_exists('missing.txt')
    assert fp is None


@pytest.mark.asyncio
async def test_file():
    fp = await open_if_exists('LICENSE', 'r')
    assert fp is not None

    content = await fp.read(3)
    assert content == 'BSD'

    await fp.close()
