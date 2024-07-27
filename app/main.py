import asyncio
import argparse
import re
import sys
from asyncio.streams import StreamReader, StreamWriter
from pathlib import Path

GLOBALS = {}

def stderr(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)

def parse_request(content: bytes) -> tuple[str, str, dict[str, str], str]:
    """Parses an HTTP request."""
    first_line, *tail = content.split(b"\r\n")
    method, path, _ = first_line.split(b" ")
    headers: dict[str, str] = {}
    while (line := tail.pop(0)) != b"":
        key, value = line.split(b": ")
        headers[key.decode()] = value.decode()
    return method.decode(), path.decode(), headers, b"".join(tail).decode()

def make_response(
    status: int,
    headers: dict[str, str] | None = None,
    body: str = "",
) -> bytes:
    """Creates an HTTP response."""
    headers = headers or {}
    msg = {
        200: "OK",
        201: "Created",
        404: "Not Found",
    }
    return b"\r\n".join(
        map(
            lambda i: i.encode(),
            [
                f"HTTP/1.1 {status} {msg[status]}",
                *[f"{k}: {v}" for k, v in headers.items()],
                f"Content-Length: {len(body)}",
                "",
                body,
            ],
        ),
    )

async def handle_connection(reader: StreamReader, writer: StreamWriter) -> None:
    """Handles a single client connection."""
    data = await reader.read(2**16)  # Read up to 64k bytes
    method, path, headers, body = parse_request(data)
    
    if method == "GET":
        if re.fullmatch(r"/", path):
            writer.write(make_response(200))
        elif match := re.fullmatch(r"/files/(.+)", path):
            file_path = Path(GLOBALS["DIR"]) / match.group(1)
            if file_path.is_file():
                content = file_path.read_text()
                writer.write(
                    make_response(
                        200,
                        {"Content-Type": "application/octet-stream"},
                        content,
                    )
                )
            else:
                writer.write(make_response(404))
        elif re.fullmatch(r"/user-agent", path):
            user_agent = headers.get("User-Agent", "")
            writer.write(
                make_response(
                    200,
                    {"Content-Type": "text/plain"},
                    user_agent,
                )
            )
        elif re.fullmatch(r"/echo/.+", path):
            response_body = path[len("/echo/"):]
            writer.write(
                make_response(
                    200,
                    {"Content-Type": "text/plain"},
                    response_body,
                )
            )
        else:
            writer.write(make_response(404))
    
    elif method == "POST":
        if match := re.fullmatch(r"/files/(.+)", path):
            file_path = Path(GLOBALS["DIR"]) / match.group(1)
            file_path.write_text(body)
            writer.write(make_response(201))
        else:
            writer.write(make_response(404))
    
    else:
        writer.write(make_response(404))

    await writer.drain()
    writer.close()

async def main():
    """Starts the HTTP server."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default=".")
    args = parser.parse_args()
    GLOBALS["DIR"] = args.directory
    
    server = await asyncio.start_server(handle_connection, "localhost", 4221)
    async with server:
        stderr("Starting server...")
        stderr(f"--directory {GLOBALS['DIR']}")
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
