import os

import aiofiles


async def open_if_exists(filename, mode="rb"):
    """Returns a file descriptor for the filename if that file exists,
    otherwise ``None``.
    """
    if not os.path.isfile(filename):
        return None

    return await aiofiles.open(filename, mode)
