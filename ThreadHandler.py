import socket
import selectors
from threading import Thread

import ReadWrite

class ThreadHandler (Thread):
    def __init__(self,sType, host, port):
        Thread.__init__(self)
        # Network components
        self._host = host
        self._port = port
        self._type = sType
        self._listening_socket = None
        self._selector = selectors.DefaultSelector()

        # Processing Components
        self._threads = {} #Dictionary of threads, threadname : thread
        self._threadNamer = 0 #Determines int name for thread. Does not equal the number of running threads

        self.readCommands = [] #SENDERTHREAD|SERVICE|MESSAGE
        self.writeCommands = [] #SENDERTHREAD|SERVICE|MESSAGE

    def DefineThreadNodeType(self,threadNum,input):
        self._threads[int(threadNum)].DefinePeerType(input)

    def _configureServer(self):
        self._listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Avoid bind() exception: OSError: [Errno 48] Address already in use
        self._listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listening_socket.bind((self._host, self._port))
        self._listening_socket.listen()

        print(f"{self._type}({self._host},{self._port}): listening on", (self._host, self._port))
        self._listening_socket.setblocking(False)
        self._selector.register(self._listening_socket, selectors.EVENT_READ, data=None)

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read

        conn.setblocking(False)

        module = None
        module = ReadWrite.ReadWrite(conn, addr, self._port, self._host, self._threadNamer,self._type)
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
            print(f"{self._type}({self._host},{self._port}): caught keyboard interrupt, exiting")
        finally:
            self._selector.close()

    def CollateThread(self): #loop through all running threads to get commands and add to outgoing commands list, to be read and processed by Node.py
        for x in self._threads:
            commandsToStore = self._threads[x].OffloadCommands() #get all stored read commands for this thread
            for y in commandsToStore: #loop through commands
                self.readCommands.append(str(self._threads[x].myName) + "|" + y)

    def WriteToBuffer(self):
        commandsCopy = self.writeCommands.copy()

        for x in commandsCopy: #commands are already routed to their handler at this stage therefore we just need to post them
            if x is None: #Case of no response required
                break
            else:
                connectionLoader = x.split("|")
                self._threads[int(connectionLoader[0])].postMessage("|".join(connectionLoader[1:]))
                del self.writeCommands[self.writeCommands.index(x)]


    def ContactNode(self,ConNodeIP,ConNodePort,commands,messageType): #For node to node. messageType = @REG, @REP etc.
        sockVar = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sockVar.connect((ConNodeIP,ConNodePort))
        sockVar.setblocking(False)

        module = ReadWrite.ReadWrite(sockVar, (ConNodeIP,ConNodePort), self._port, self._host, self._threadNamer,self._type)
        newThreadName = self._threadNamer
        self._threads[newThreadName] = module
        self._threadNamer = self._threadNamer + 1
        module.start()
        message = messageType + "|" + str(self._type) + "|" + str(self._host) + "|" + str(self._port)

        for x in commands: #Append list of any commands this node can handle, for routing later.
            message += "|" + x

        module.postMessage(message) #Tell parent what IP and Port this node exists on
        return newThreadName #Return the thread that has been created

    def GetThreadInfo(self,threadID): #Return the IP and Port of a specified ReadWrite Thread
        return self._threads[int(threadID)].GetSocket()