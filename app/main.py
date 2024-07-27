#!/usr/bin/env python3
"""Code written by Kalkulus (https://github.com/Kalkulus1) for CodeCrafters.io."""
import socket
from threading import Thread
import argparse
from pathlib import Path
import gzip
from io import BytesIO
from typing import Dict

# Constants
RN = b"\r\n"  # Carriage return and newline bytes for HTTP headers separation


def parse_request(conn: socket.socket) -> Dict[str, any]:
    """
    Parses an HTTP request from the client connection.

    This function reads data from the provided socket connection and
    parses the HTTP request into its components:
    - request line (method, URL, and HTTP version)
    - headers
    - body (if present)

    Args:
        conn (socket.socket): The client connection to read from.

    Returns:
        Dict[str, any]: A dictionary containing:
            - 'method': HTTP method (e.g., GET, POST)
            - 'url': Request URL
            - 'headers': HTTP headers as a dictionary
            - 'body': Request body as bytes
    """
    request_data = {}
    headers = {}
    body_chunks = []
    target_phase = 0  # 0: request line, 1: headers, 2: body
    remaining_data = b""
    body_length = 0
    body_received = 0

    while data := conn.recv(1024):
        if remaining_data:
            data = remaining_data + data
            remaining_data = b""

        if target_phase == 0:
            # Process the request line (e.g., GET /path HTTP/1.1)
            header_end_idx = data.find(RN)
            if header_end_idx == -1:
                remaining_data = data
                continue

            request_line = data[:header_end_idx].decode()
            data = data[header_end_idx + 2 :]
            request_data["request"] = request_line
            method, url, _ = request_line.split()
            request_data["method"] = method
            request_data["url"] = url
            target_phase = 1  # Move to headers

        if target_phase == 1:
            if not data:
                continue

            while True:
                header_end_idx = data.find(RN)
                if header_end_idx == -1:
                    remaining_data = data
                    break

                if header_end_idx == 0:  # End of headers section
                    data = data[header_end_idx + 2 :]
                    target_phase = 2
                    break

                header_line = data[:header_end_idx].decode()
                data = data[header_end_idx + 2 :]
                if ":" in header_line:
                    key, value = header_line.split(":", maxsplit=1)
                    headers[key.strip().lower()] = value.strip()

            if target_phase == 1:
                continue

        if target_phase == 2:
            if "content-length" not in headers:
                break

            body_length = int(headers["content-length"])
            if not body_length:
                break

            target_phase = 3

        if target_phase == 3:
            body_chunks.append(data)
            body_received += len(data)
            if body_received >= body_length:
                break

    request_data["headers"] = headers
    request_data["body"] = b"".join(body_chunks)
    return request_data


def compress_gzip(data: bytes) -> bytes:
    """
    Compresses the given data using gzip compression.

    Args:
        data (bytes): The data to be compressed.

    Returns:
        bytes: The gzip-compressed data.
    """
    buffer = BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb") as gz_file:
        gz_file.write(data)
    return buffer.getvalue()


def handle_request(conn: socket.socket, dir_path: str) -> None:
    """
    Handles an incoming HTTP request and sends the appropriate response.

    This function reads the HTTP request from the connection, processes it,
    and sends back a response. The response may include gzip compression
    based on the `Accept-Encoding` header.

    Args:
        conn (socket.socket): The client connection.
        dir_path (str): The directory from which to serve files.
    """
    with conn:
        request_data = parse_request(conn)
        url = request_data["url"]
        method = request_data["method"]
        headers = request_data["headers"]
        body = request_data["body"]

        if url == "/":
            conn.sendall(b"HTTP/1.1 200 OK\r\n\r\n")
        elif url.startswith("/echo/"):
            response_body = url[6:].encode()
            accept_encoding = headers.get("accept-encoding", "")
            if "gzip" in accept_encoding.split(", "):
                compressed_body = compress_gzip(response_body)
                response_headers = [
                    b"HTTP/1.1 200 OK\r\n",
                    b"Content-Type: text/plain\r\n",
                    b"Content-Encoding: gzip\r\n",
                    f"Content-Length: {len(compressed_body)}\r\n".encode(),
                    RN,
                ]
                conn.sendall(b"".join(response_headers))
                conn.sendall(compressed_body)
            else:
                response_headers = [
                    b"HTTP/1.1 200 OK\r\n",
                    b"Content-Type: text/plain\r\n",
                    f"Content-Length: {len(response_body)}\r\n".encode(),
                    RN,
                ]
                conn.sendall(b"".join(response_headers))
                conn.sendall(response_body)
        elif url == "/user-agent":
            user_agent = headers.get("user-agent", "").encode()
            conn.send(b"HTTP/1.1 200 OK\r\n")
            conn.send(b"Content-Type: text/plain\r\n")
            conn.send(f"Content-Length: {len(user_agent)}\r\n".encode())
            conn.send(RN)
            conn.send(user_agent)
        elif url.startswith("/files/"):
            file_path = Path(dir_path) / url[7:]
            if method == "GET":
                if file_path.exists():
                    conn.send(b"HTTP/1.1 200 OK\r\n")
                    conn.send(b"Content-Type: application/octet-stream\r\n")
                    with open(file_path, "rb") as file:
                        file_body = file.read()
                    conn.send(f"Content-Length: {len(file_body)}\r\n".encode())
                    conn.send(RN)
                    conn.send(file_body)
                else:
                    conn.sendall(b"HTTP/1.1 404 Not Found\r\n\r\n")
            elif method == "POST":
                with open(file_path, "wb") as file:
                    file.write(body)
                conn.send(b"HTTP/1.1 201 Created\r\n\r\n")
            else:
                conn.sendall(b"HTTP/1.1 404 Not Found\r\n\r\n")
        else:
            conn.sendall(b"HTTP/1.1 404 Not Found\r\n\r\n")


def main() -> None:
    """
    Starts the HTTP server and handles incoming connections.

    This function sets up the server socket to listen for incoming connections
    on localhost at port 4221. It then accepts incoming connections and spawns
    a new thread to handle each request.
    """
    parser = argparse.ArgumentParser(
        description="A simple HTTP server with gzip compression support."
    )
    parser.add_argument(
        "--directory", default=".", help="Directory to serve files from"
    )
    args = parser.parse_args()

    # Create a server socket
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)

    # Accept incoming connections and handle them in separate threads
    while True:
        conn, _ = server_socket.accept()
        Thread(target=handle_request, args=(conn, args.directory)).start()


if __name__ == "__main__":
    main()
