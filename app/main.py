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
    def __init__(self, request_line: str, headers: dict[str, str], body: str):
        method, target, version = request_line.split(" ", 2)

        self.method = HttpMethod[method]
        self.target = target
        self.version = version
        self.headers = headers
        self.body = body


class HttpResponse:
    def __init__(
        self,
        status_code: HttpStatus,
        headers: dict[str, str] = dict(),
        body: str | None = None,
    ):
        self.status_code = status_code
        self.headers = headers
        self.body = body

        if self.body:
            self.headers["Content-Length"] = str(len(self.body))

    def __str__(self):
        headers = "\r\n".join([f"{key}: {value}\r\n" for key, value in self.headers])
        return f"HTTP/1.1 {self.status_code.code} {self.status_code.reason}\r\n{headers}\r\n{self.body}"


class HttpServer:
    def __init__(self, host: str, port: int):
        self.socket = socket.create_server((host, port), reuse_port=True)

    def run(self):
        while True:
            (client, _) = self.socket.accept()
            (request_line, headers, body) = self.__read_req(client)
            response = self.__route(HttpRequest(request_line, headers, body))
            self.__send_response(client, response)

            client.close()

    def __route(self, req: HttpRequest) -> HttpResponse:
        match req.target.lstrip("/").split("/"):
            case [""]:
                return HttpResponse(HttpStatus.OK)
            case ["echo", msg]:
                return HttpResponse(
                    HttpStatus.OK, {"Content-Type": "application/text"}, msg
                )
            case _:
                return HttpResponse(HttpStatus.NOT_FOUND)

    def __send_response(self, client: socket.socket, res: HttpResponse):
        client.sendall(str(res).encode())

    def __read_req(self, client: socket.socket) -> tuple[str, dict, str]:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = client.recv(1024)
            if not chunk:
                break
            data += chunk

        header_section, _, body = data.partition(b"\r\n\r\n")

        headers = {}
        request_line, *header_lines = header_section.split(b"\r\n")
        for header in header_lines:
            if not header:
                continue

            key, value = header.split(b":", 1)
            headers[key.strip().lower().decode()] = value.strip().decode()

        content_length = int(headers.get("content-length", 0))

        while len(body) < content_length:
            chunk = client.recv(1024)
            if not chunk:
                break
            body += chunk

        return (request_line.decode("utf-8"), headers, body.decode("utf-8"))


def main():
    print("Logs from your program will appear here!")

    server = HttpServer("localhost", 4221)
    server.run()


if __name__ == "__main__":
    main()
