"""Simple TCP server to verify inbound connectivity.

Run this script on the target server. It listens for a single client,
prints the received message, sends a confirmation response, and exits.
"""
from __future__ import annotations

import argparse
import socket
from datetime import datetime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lightweight TCP server for connection testing",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Interface to bind (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9000,
        help="Port to listen on (default: 9000)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((args.host, args.port))
        sock.listen(1)
        print(f"Listening on {args.host}:{args.port} …")

        client_sock, addr = sock.accept()
        with client_sock:
            print(f"Connection received from {addr[0]}:{addr[1]}")
            data = client_sock.recv(1024)
            message = data.decode("utf-8", errors="replace") if data else ""
            if message:
                print(f"Received message: {message}")
            else:
                print("Client connected but did not send a message.")

            response = f"ACK from server at {datetime.utcnow().isoformat()}Z"
            client_sock.sendall(response.encode("utf-8"))
            print("Acknowledgement sent; closing connection.")


if __name__ == "__main__":
    main()
