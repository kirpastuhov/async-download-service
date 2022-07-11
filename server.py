import asyncio
import os

import aiofiles
from aiohttp import web
from loguru import logger


def verify_path(path: str):
    return os.path.exists(path)


async def archive(request):
    archive_hash = request.match_info.get("archive_hash")
    archive_path = os.path.join("test_photos", archive_hash)

    if not verify_path(archive_path):
        raise web.HTTPNotFound(text="Archive with such name doesn't exist")

    response = web.StreamResponse()
    response.headers["Content-Disposition"] = f'attachment; filename="{archive_hash}.zip"'

    await response.prepare(request)

    i = 1
    buffer_size = 100_000  # bytes
    cmd = f"zip -r -j - {archive_path}"
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

    while True:
        i += 1
        stdout = await proc.stdout.read(n=buffer_size)
        logger.debug("Sending archive chunk...")
        await response.write(stdout)

        if proc.stdout.at_eof():
            break


async def handle_index_page(request):
    async with aiofiles.open("index.html", mode="r") as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type="text/html")


if __name__ == "__main__":
    app = web.Application()
    app.add_routes(
        [
            web.get("/", handle_index_page),
            web.get("/archive/{archive_hash}/", archive),
        ]
    )
    web.run_app(app)
