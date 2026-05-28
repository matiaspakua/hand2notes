"""Server entry point.

Selects a free port (or honours the PORT env var), announces it on stdout as
`HAND2NOTES_PORT=<port>` so the Electron main process can connect, then serves.
"""

import os
import socket

import uvicorn


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main() -> None:
    port = int(os.environ.get("PORT") or _free_port())
    # Flushed immediately so the parent process can parse it before requests start.
    print(f"HAND2NOTES_PORT={port}", flush=True)
    uvicorn.run("hand2notes.api.main:app", host="127.0.0.1", port=port, log_config=None)


if __name__ == "__main__":
    main()
