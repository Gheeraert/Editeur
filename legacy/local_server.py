from __future__ import annotations

import contextlib
import socket
import threading
import webbrowser
from dataclasses import dataclass, field
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


@dataclass(slots=True)
class PreviewServer:
    """Petit serveur HTTP local pour prévisualiser le site généré."""

    directory: Path
    host: str = "127.0.0.1"
    preferred_ports: tuple[int, ...] = (8000, 8080)
    _thread: threading.Thread | None = field(init=False, default=None, repr=False)
    _httpd: ThreadingHTTPServer | None = field(init=False, default=None, repr=False)
    port: int | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.directory = self.directory.resolve()

    def start(self) -> str:
        if self._httpd is not None and self.port is not None:
            return self.base_url

        port = self._find_port()
        handler = partial(SimpleHTTPRequestHandler, directory=str(self.directory))
        self._httpd = ThreadingHTTPServer((self.host, port), handler)
        self.port = port
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self.base_url

    def stop(self) -> None:
        if self._httpd is None:
            return
        self._httpd.shutdown()
        self._httpd.server_close()
        self._httpd = None
        self.port = None
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    @property
    def base_url(self) -> str:
        if self.port is None:
            raise RuntimeError("Le serveur local n'est pas démarré.")
        return f"http://{self.host}:{self.port}"

    def open_in_browser(self, relative_path: str = "index.html") -> str:
        relative = relative_path.lstrip("/")
        url = f"{self.base_url}/{relative}" if relative else self.base_url
        webbrowser.open_new_tab(url)
        return url

    def _find_port(self) -> int:
        for port in self.preferred_ports:
            if self._port_is_free(port):
                return port
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.bind((self.host, 0))
            sock.listen(1)
            return int(sock.getsockname()[1])

    def _port_is_free(self, port: int) -> bool:
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(0.2)
            try:
                sock.bind((self.host, port))
                return True
            except OSError:
                return False
