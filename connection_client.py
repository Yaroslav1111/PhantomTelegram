"""Simple TCP client to verify connectivity to a server.

Run this script on your local machine. It connects to the server, sends a
short message, waits for a reply, and prints the result.
"""
from __future__ import annotations

import argparse
import socket
import sys
from datetime import datetime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lightweight TCP client for connection testing",
    )
    parser.add_argument(
        "host",
        help="Hostname or IP address of the server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9000,
        help="Port to connect to (default: 9000)",
    )
    parser.add_argument(
        "--message",
        default="Hello from the client!",
        help="Message to send to the server",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Connection timeout in seconds (default: 5)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = f"[{datetime.utcnow().isoformat()}Z] {args.message}".encode("utf-8")

    try:
        with socket.create_connection((args.host, args.port), timeout=args.timeout) as sock:
            sock.sendall(payload)
            response = sock.recv(1024).decode("utf-8", errors="replace")
            print(f"Received response: {response}")
    except OSError as exc:
        print(f"Connection failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
