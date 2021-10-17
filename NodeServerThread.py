import queue
import socket
import selectors
import echo
import dict
from threading import Thread
import types

class NodeServerThread (Thread):
    def __init__(self, sock, addr, myPort, myIP, myType):
        Thread.__init__(self)
        # Network components
        self._listening_socket = None
        self._sock = sock
        self._addr = addr

        self._myIP = myIP
        self._myPort = myPort
        self._myType = myType

        self._selector = selectors.DefaultSelector()
        self._running = True

        self._outgoing_buffer = queue.Queue()

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self._selector.register(self._sock, events, data=None)

    def kill_connection(self):
        self._running = False

    def run(self):
        print("\033[92m" + f"Server({self._myIP},{self._myPort})T: entered run on {self._sock.getsockname()}" + "\033[0m")
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
        print("\033[92m" + f"Server({self._myIP},{self._myPort})T: entered read on {key.fileobj.getsockname()}" + "\033[0m")
        recv_data = self._sock.recv(1024).decode()
        if recv_data:
            print(f"Server({self._myIP},{self._myPort})T: received", repr(recv_data), "from connection", repr(key.fileobj.getpeername()))
            self._response(key) # Calls response writer
        if not recv_data:
            print(f"Server({self._myIP},{self._myPort})T: closing connection on " , repr(key.fileobj.getpeername()))
            self._selector.unregister(self._sock)
            self._sock.close()

    def _response(self,key):
        if self._myType == "Control":
            self.postMessage("Hi! Im a Control Node that exists on ({self._myIP},{self._myPort})")
        elif self._myType == "Echo":
            self.postMessage("AAA")
            #Implement code for echo.py call

    def _write(self, key):
        print("\033[92m" + f"Server({self._myIP},{self._myPort})T: entered write on {key.fileobj.getsockname()}" + "\033[0m")
        try:
            message = self._outgoing_buffer.get_nowait()
        except queue.Empty:
            message = None
        if message:
            print("\033[92m" + f"Server({self._myIP},{self._myPort}): sent message '{message}' \033[0m")
            sent = self._sock.send(message.encode())

    def postMessage(self, message):
        self._outgoing_buffer.put(message)
