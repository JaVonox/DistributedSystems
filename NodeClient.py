import queue
import socket
import selectors
from threading import Thread
import types

class NodeClient (Thread):
    def __init__(self, name, host="127.0.0.1", port=12346):
        Thread.__init__(self)
        # Network components
        self._host = host
        self._port = port
        self._listening_socket = None
        self._sock = None
        self._selector = selectors.DefaultSelector()
        self._name = name
        self._running = True

        self._outgoing_buffer = queue.Queue()

        addr = (host, port)

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setblocking(False)
        self._sock.connect_ex(addr)
        self._ownPort = self._sock.getsockname()[1]
        self._ownIP = self._sock.getsockname()[0]

        print(f"Client({self._ownIP},{self._ownPort}): starting connection to", addr)

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self._selector.register(self._sock, events, data=None)

    def get_port(self):
        return self._ownPort

    def get_ip(self):
        return self._ownIP

    def kill_connection(self):
        self._running = False

    def run(self):
        print("\033[94m" + f"Client({self._ownIP},{self._ownPort}): entered run \033[0m")
        try:
            while self._running:
                events = self._selector.select(timeout=1)
                for key, mask in events:
                    if mask & selectors.EVENT_READ:
                        self._read(key)
                    if mask & selectors.EVENT_WRITE and not self._outgoing_buffer.empty():
                        self._write(key)
                # Check for a socket being monitored to continue.
                if not self._selector.get_map():
                    break
        except KeyboardInterrupt:
            pass
        finally:
            self._selector.close()

    def _read(self, key):
        print("\033[94m" + f"Client({self._ownIP},{self._ownPort}): entered read \033[94m")
        recv_data = self._sock.recv(1024).decode()
        if recv_data:
            print("\033[94m" + f"Client({self._ownIP},{self._ownPort}): received", repr(recv_data), "from connection", repr(key.fileobj.getpeername()) + "\033[94m")
        if not recv_data:
            print(f"Client({self._ownIP},{self._ownPort}): closing connection", repr(key))
            self._selector.unregister(self._sock)
            self._sock.close()

    def _write(self, key):
        print("\033[94m" + f"Client({self._ownIP},{self._ownPort}): entered write \033[0m")
        try:
            message = self._outgoing_buffer.get_nowait()
        except queue.Empty:
            message = None
        if message:
            print("\033[94m" + f"Client({self._ownIP},{self._ownPort}): sent message '{message}' \033[0m")
            sent = self._sock.send(message.encode())

    def postMessage(self, message):
        self._outgoing_buffer.put(message)