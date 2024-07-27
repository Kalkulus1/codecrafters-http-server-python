# Uncomment this to pass the first stage
import socket


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    # Uncomment this to pass the first stage
    #
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    sock, addr = server_socket.accept()
    sock.sendall(b"HTTP/1.1 200 OK\r\n\r\n")


if __name__ == "__main__":
    main()
