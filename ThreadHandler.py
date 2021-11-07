import socket
import selectors
from threading import Thread

import ReadWrite

class ThreadHandler (Thread):
    def __init__(self,sType, host="127.0.0.1", port=12345):
        Thread.__init__(self)
        # Network components
        self._host = host
        self._port = port
        self._serverType = sType
        self._listening_socket = None
        self._selector = selectors.DefaultSelector()

        # Processing Components
        self._threads = {} #Dictionary of threads, threadname : thread
        self._threadNamer = 0 #Determines int name for thread. Does not equal the number of running threads

        self.readCommands = [] #SENDERTHREAD|SERVICE|MESSAGE
        self.writeCommands = [] #SENDERTHREAD|SERVICE|MESSAGE

    def _configureServer(self):
        self._listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Avoid bind() exception: OSError: [Errno 48] Address already in use
        self._listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listening_socket.bind((self._host, self._port))
        self._listening_socket.listen()

        print(f"Server({self._host},{self._port}): listening on", (self._host, self._port))
        self._listening_socket.setblocking(False)
        self._selector.register(self._listening_socket, selectors.EVENT_READ, data=None)

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        print(f"Server({self._host},{self._port}): accepted connection from", addr)

        conn.setblocking(False)

        module = None
        module = ReadWrite.ReadWrite(conn, addr, self._port, self._host, self._threadNamer)
        self._threads[self._threadNamer] = module
        self._threadNamer = self._threadNamer + 1
        module.start()

    def run(self):
        self._configureServer()
        try:
            while True:
                events = self._selector.select(timeout=0.01) #loop every second

                self.WriteToBuffer() #write any inputs that have been provided by node.py
                self.CollateThread() #collect any inputs from threads
                for key, mask in events:
                    if key.data is None:
                        self.accept_wrapper(key.fileobj) #add new connection to modules
                    else:
                       pass
        except KeyboardInterrupt:
            print(f"Server({self._host},{self._port}): caught keyboard interrupt, exiting")
        finally:
            self._selector.close()

    def CollateThread(self): #loop through all running threads to get commands and add to outgoing commands list, to be read and processed by Node.py
        for x in self._threads:
            commandsToStore = self._threads[x].OffloadCommands() #get all stored read commands for this thread
            for y in commandsToStore: #loop through commands
                self.readCommands.append(str(self._threads[x].myName) + "|" + y)

    def WriteToBuffer(self):
        commandsToKill = []

        for x in self.writeCommands: #commands are already routed to their handler at this stage therefore we just need to post them
            connectionLoader = x.split("|")
            self._threads[int(connectionLoader[0])].postMessage(connectionLoader[1])
            commandsToKill.append(self.writeCommands.index(x))

        for z in commandsToKill: #clear all processed commands
            del self.writeCommands[int(z)]

    def ContactParent(self,parentIP,parentPort,nodeType):
        sockVar = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #sockVar.setblocking(False)
        sockVar.connect((parentIP,parentPort))


        module = ReadWrite.ReadWrite(sockVar, (parentIP,parentPort), self._port, self._host, self._threadNamer)
        self._threads[self._threadNamer] = module
        self._threadNamer = self._threadNamer + 1
        module.start()
        module.postMessage("REG|" + nodeType + "|" + str(self._host) + "|" + str(self._port))