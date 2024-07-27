import socket
import threading



def handle_client(sock):
    with sock:
        request = sock.recv(1024).decode('utf-8')
        print(f"Received request: {request}")

        # Parse the request line and headers
        lines = request.split("\r\n")
        request_line = lines[0]
        method, path, _ = request_line.split()
        headers = {key: value for (key, value) in (line.split(": ", 1) for line in lines[1:] if ": " in line)}

        # Check for the /user-agent endpoint
        if path == "/user-agent":
            user_agent = headers.get("User-Agent", "")
            response_body = user_agent
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                f"Content-Length: {len(response_body)}\r\n"
                "\r\n"
                f"{response_body}"
            )
        elif path.startswith("/echo/"):
            response_body = path[len("/echo/"):]
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                f"Content-Length: {len(response_body)}\r\n"
                "\r\n"
                f"{response_body}"
            )
        elif path == "/":
            response = "HTTP/1.1 200 OK\r\n\r\n"
        else:
            response = "HTTP/1.1 404 Not Found\r\n\r\n"

        sock.sendall(response.encode('utf-8'))

def main():
    print("Logs from your program will appear here!")

    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    server_socket.listen()

    while True:
        client_sock, addr = server_socket.accept()
        print(f"Accepted connection from {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client_sock,))
        client_handler.start()


if __name__ == "__main__":
    main()
