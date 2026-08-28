from enum import Enum, StrEnum
from collections.abc import Buffer
import socket  # noqa: F401


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class HttpStatus(Enum):
    OK = (200, "OK")
    NOT_FOUND = (404, "Not Found")

    def __init__(self, code, reason):
        self.code = code
        self.reason = reason


class HttpRequest:
    def __init__(self, data: str):
        request_line, *header_lines = data.split("\r\n")

        method, target, version = request_line.split(" ", 2)

        headers = {}
        for header in header_lines:
            if not header:
                continue

            key, value = header.split(":", 1)
            headers[key.strip()] = value.strip()

        self.method = HttpMethod[method]
        self.target = target
        self.version = version
        self.headers = headers


class HttpResponse:
    def __init__(self, status_code: HttpStatus):
        self.status_code = status_code

    def __str__(self):
        return f"HTTP/1.1 {self.status_code.code} {self.status_code.reason}\r\n\r\n"


class HttpServer:
    def __init__(self, host: str, port: int):
        self.socket = socket.create_server((host, port), reuse_port=True)

    def run(self):
        while True:
            (client, _) = self.socket.accept()
            data = self.__read_req(client)

            self.__send_response(client, HttpRequest(data))

    def __send_response(self, socket: socket.socket, req: HttpRequest):
        match req.target:
            case "/":
                socket.sendall(str(HttpResponse(HttpStatus.OK)).encode())
            case _:
                socket.sendall(str(HttpResponse(HttpStatus.NOT_FOUND)).encode())

    def __read_req(self, client: socket.socket) -> str:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = client.recv(1024)
            if not chunk:
                break
            data += chunk
        return data.decode("utf-8")


def main():
    print("Logs from your program will appear here!")

    server = HttpServer("localhost", 4221)
    server.run()


if __name__ == "__main__":
    main()
