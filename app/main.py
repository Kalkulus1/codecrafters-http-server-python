# Uncomment this to pass the first stage
import socket


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    # Uncomment this to pass the first stage
    #
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    
    while True:
        sock, addr = server_socket.accept()
        with sock:
            request = sock.recv(1024).decode('utf-8')
            print(f"Received request: {request}")

            # Parse the request line
            request_line = request.split("\r\n")[0]
            method, path, _ = request_line.split()

            # Check for the /echo/ endpoint
            if path.startswith("/echo/"):
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


if __name__ == "__main__":
    main()
