import queue
import socket
import selectors
from threading import Thread
import types

class ReadWrite (Thread):
    def __init__(self, sock, addr, myPort, myIP, myName, myNodeType):
        Thread.__init__(self)
        # Network components
        self._sock = sock
        self._addr = addr
        self._myNodeType = myNodeType
        self._peerNodeType = "Node"

        self._myIP = myIP
        self._myPort = myPort
        self.myName = myName

        self._selector = selectors.DefaultSelector()
        self._running = True

        self._outgoing_buffer = queue.Queue() # Write to this to organise response
        self._readBuffer = [] #this is written to for read inputs. It will include a module name of the desired module reader.

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self._selector.register(self._sock, events, data=None)

    def kill_connection(self):
        self._running = False

    def DefinePeerType(self,type):
        self._peerNodeType = type

    def run(self):
        try:
            while self._running:
                events = self._selector.select(timeout=1)
                for key, mask in events:
                    if mask & selectors.EVENT_READ: #Equivalent to mask == event read
                        self._read(key)
                    if mask & selectors.EVENT_WRITE and not self._outgoing_buffer.empty(): #Equivalent to mask == event write
                        self._write(key)
                # Check for a socket being monitored to continue.
                if not self._selector.get_map():
                    break
        except KeyboardInterrupt:
            pass
        finally:
            self._selector.close()

    def _read(self, key):
        recv_data = self._sock.recv(1024).decode()
        if recv_data:
            print(f"{self._peerNodeType}({key.fileobj.getpeername()[0]},{key.fileobj.getpeername()[1]}):", repr(recv_data))
            self._readBuffer.append(recv_data) #adds read data into the read buffer
        if not recv_data:
            print(f"{self._myNodeType}({self._myIP},{self._myPort})RWT{self.myName}: closing connection on " , repr(key.fileobj.getpeername()))
            self._selector.unregister(self._sock)
            self._sock.close()

    def _write(self, key):
        try:
            message = self._outgoing_buffer.get(False)
        except queue.Empty:
            message = None
        if message == "#":
            pass #Switches to read mode if the output message is the NOOP (#) command
        elif message:
            print(f"{self._myNodeType}({self._myIP},{self._myPort})RWT{self.myName}: sent message '{message}' to {self._peerNodeType}({key.fileobj.getpeername()[0]},{key.fileobj.getpeername()[1]})")
            sent = self._sock.send(message.encode())

    def OffloadCommands(self): #return all stored reads and clear the buffer
        commands = []
        commands = self._readBuffer.copy()
        self._readBuffer.clear()
        return commands

    def postMessage(self, message):
        self._outgoing_buffer.put(message)

    def GetSocket(self): #get info of connected client
        return self._sock.getpeername()
