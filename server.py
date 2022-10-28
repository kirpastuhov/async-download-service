import argparse
import asyncio
import os

import aiofiles
from aiohttp import web
from loguru import logger


async def archive(request):
    photo_dir = request.app["photo_dir"]
    delay = request.app["delay"]

    archive_hash = request.match_info["archive_hash"]
    archive_path = os.path.join(photo_dir, archive_hash)

    if not os.path.exists(archive_path):
        raise web.HTTPNotFound(text="Archive with such name doesn't exist")

    response = web.StreamResponse()
    response.headers["Content-Disposition"] = f"attachment; filename={archive_hash}.zip"

    await response.prepare(request)

    chunk_number = 0
    buffer_size = 100_000  # bytes
    cmd = f"zip -rq - {archive_path}"
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

    try:
        while not proc.stdout.at_eof():
            chunk_number += 1
            stdout = await proc.stdout.read(n=buffer_size)
            logger.debug(f"Sending archive chunk # {chunk_number}...")
            await response.write(stdout)
            await asyncio.sleep(delay)
        await response.write_eof()
        logger.info("Archive sent")
    except asyncio.CancelledError:
        response.force_close()
        logger.error("Download was cancelled")
        raise
    except Exception as e:
        response.force_close()
        logger.error(f"Server error {str(e)}")
        return web.HTTPServerError()
    finally:
        if proc.returncode is not None:
            proc.kill()
            await proc.communicate()


async def handle_index_page(request):
    async with aiofiles.open("index.html", mode="r") as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type="text/html")


def main():
    parser = argparse.ArgumentParser(description="Server settings")
    parser.add_argument("--quiet", action=argparse.BooleanOptionalAction, help="Enable/disable logging")
    parser.add_argument("--photo_dir", dest="photo_dir", type=str, default="test_photos", help="Directory with photos.")
    parser.add_argument("--delay", dest="delay", default=0, type=int, help="Response delay in seconds")
    args = parser.parse_args()

    if args.quiet:
        logger.disable(__name__)

    app = web.Application()

    app["delay"] = args.delay
    app["photo_dir"] = args.photo_dir

    app.add_routes(
        [
            web.get("/", handle_index_page),
            web.get("/archive/{archive_hash}/", archive),
        ]
    )
    web.run_app(app)


if __name__ == "__main__":
    main()
