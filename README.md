# aioja
Async version of Jinja2.

[![PyPI](https://img.shields.io/pypi/v/aioja.svg)](https://pypi.org/project/aioja/)
[![Build Status](https://travis-ci.org/dldevinc/aioja.svg?branch=master)](https://travis-ci.org/dldevinc/aioja)

This library contains a modification of the Jinja2 library. 
In addition to Jinja's built-in `render_async`, i've added:
* async `FileSystemLoader` (via [aiofiles](https://github.com/Tinche/aiofiles))
* async bytecode cache ([aioredis](https://github.com/aio-libs/aioredis) and [aiocache](https://github.com/argaen/aiocache) supported)
* async version of the `Environment.compile_templates` method

## Install

```
pip install aioja
```

## Quick Start

```python
from aioja.environment import Environment
from aioja.loaders import FileSystemLoader
from aioja.bccache.aiocache import AioCacheBytecodeCache


env = Environment(
    loader=FileSystemLoader('templates'),
    # ...
    # bytecode_cache=AioCacheBytecodeCache()
    # ...
)

template = await env.get_template('index.html')
content = await template.render_async({
    'page_id': 123
})
```
