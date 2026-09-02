from pathlib import Path
import sys
import threading
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
    CREATED = (201, "Created")
    NOT_FOUND = (404, "Not Found")
    INTERNAL_ERROR = (500, "Internal Server Error")

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
    _guard = object()

    def __init__(
        self,
        guard,
        status_code: HttpStatus,
        headers: dict[str, str] = dict(),
        body: str | None = None,
    ):
        if guard is not HttpResponse._guard:
            raise TypeError("HttpResponse must be constructed via HttpResponseBuilder")

        self.status_code = status_code
        self.headers = headers
        self.body = body

        if self.body:
            self.headers["Content-Length"] = str(len(self.body))

    def __str__(self):
        headers = "\r\n".join(
            [f"{key}: {value}" for key, value in self.headers.items()]
        )
        return f"HTTP/1.1 {self.status_code.code} {self.status_code.reason}\r\n{headers}\r\n\r\n{self.body}"


class HttpResponseBuilder:
    def __init__(self):
        self._status_code: HttpStatus = HttpStatus.OK
        self._headers: dict[str, str] = {}
        self._body: str | None = None

    def status(self, status_code: HttpStatus) -> "HttpResponseBuilder":
        self._status_code = status_code
        return self

    def header(self, key: str, value: str) -> "HttpResponseBuilder":
        self._headers[key] = value
        return self

    def headers(self, headers: dict[str, str]) -> "HttpResponseBuilder":
        self._headers.update(headers)
        return self

    def body(self, body: str) -> "HttpResponseBuilder":
        self._body = body
        return self

    def build(self) -> HttpResponse:
        return HttpResponse(
            HttpResponse._guard,
            status_code=self._status_code,
            headers=dict(self._headers),  # copy, so the builder can be reused
            body=self._body,
        )


class HttpServer:
    def __init__(self, host: str, port: int):

        if len(sys.argv) == 3 and sys.argv[1] == "--directory":
            self.directory = sys.argv[2]

        self.socket = socket.create_server((host, port), reuse_port=True)

    def run(self):
        while True:
            (client, _) = self.socket.accept()
            threading.Thread(target=self.__handle_request, args=(client,)).start()

    def __handle_request(self, client: socket.socket):
        request = self.__read_req(client)
        response = self.__route(request)

        client.sendall(str(response).encode())
        client.close()

    def __route(self, req: HttpRequest) -> HttpResponse:
        match req.target.lstrip("/").split("/"):
            case [""]:
                return HttpResponseBuilder().status(HttpStatus.OK).build()
            case ["echo", msg]:
                return (
                    HttpResponseBuilder()
                    .status(HttpStatus.OK)
                    .headers({"Content-Type": "text/plain"})
                    .body(msg)
                    .build()
                )
            case ["user-agent"]:
                return (
                    HttpResponseBuilder()
                    .status(HttpStatus.OK)
                    .header("Content-Type", "text/plain")
                    .body(req.headers.get("user-agent", ""))
                    .build()
                )
            case ["files", filename] if req.method == HttpMethod.GET:
                path = Path(self.directory) / filename
                if not path.is_file():
                    return HttpResponseBuilder().status(HttpStatus.NOT_FOUND).build()

                data = path.read_text()

                return (
                    HttpResponseBuilder()
                    .status(HttpStatus.OK)
                    .header("Content-Type", "application/octet-stream")
                    .body(data)
                    .build()
                )

            case ["files", filename] if req.method == HttpMethod.POST:
                path = Path(self.directory) / filename

                with open(path, "w") as f:
                    f.write(req.body)

                return HttpResponseBuilder().status(HttpStatus.CREATED).build()

            case _:
                return HttpResponseBuilder().status(HttpStatus.NOT_FOUND).build()

    def __read_req(self, client: socket.socket) -> HttpRequest:
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

        return HttpRequest(request_line.decode("utf-8"), headers, body.decode("utf-8"))


def main():
    print("Logs from your program will appear here!")

    server = HttpServer("localhost", 4221)
    server.run()


if __name__ == "__main__":
    main()
