import select
import socket
import struct
from typing import Any

from docker import APIClient


class ContainerProc:
    def __init__(self, sock: socket.socket, client: APIClient, exec_id: Any) -> None:
        self.sock = sock
        self.client = client
        self.exec_id = exec_id

    def write_stdin(self, data: bytes) -> None:
        self.sock.sendall(data)

    def close_stdin(self) -> None:
        self.sock.shutdown(socket.SHUT_WR)

    def is_running(self) -> bool:
        exec_inspect = self.client.exec_inspect(self.exec_id)
        return exec_inspect["Running"]

    def read_output(self, timeout_sec: float = 0) -> tuple[int | None, bytes]:
        """First value in tuple is one of:
        0: no data to read within specified timeout
        1: stdout
        2: stderr
        None: process has ended

        Second value in tuple is the data read from the stream.
        """
        rlist, _, _ = select.select([self.sock], [], [], timeout_sec)
        if self.sock in rlist:
            return _demux_multiplexed_stream(self.sock)
        else:
            return 0, b""


def _demux_multiplexed_stream(read_sock: socket.socket) -> tuple[int | None, bytes]:
    """
    Demultiplex the Docker multiplexed stream by reading the header off the
    socket to get the fd and payload size, then read the payload.
    """
    # Read the 8-byte header
    header = read_sock.recv(8)
    if len(header) == 0:
        # Connection closed
        return None, b""
    if len(header) < 8:
        # Incomplete header
        raise Exception("Incomplete header")

    stream_type = header[0]
    payload_size = struct.unpack(">I", header[4:8])[0]

    # Read the payload
    payload = b""
    while len(payload) < payload_size:
        chunk = read_sock.recv(payload_size - len(payload))
        if not chunk:
            break
        payload += chunk
    return stream_type, payload
