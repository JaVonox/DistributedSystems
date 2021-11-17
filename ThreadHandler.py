import socket
import selectors
import types
import queue
from threading import Thread

class ThreadHandler (Thread):
    def __init__(self,sType, host, port):
        Thread.__init__(self)
        # Network components
        self._host = host
        self._port = port
        self._type = sType #self type
        self._listening_socket = None
        self._selector = selectors.DefaultSelector()

        # Processing Components
        self._activeConnections = {} #Dictionary of connection, connName : key
        self._connectionNamer = 0 #Determines int name for connections. Does not equal the number of running connections

        self.readCommands = [] #SENDERNAME|SERVICE|MESSAGE data recieved (inb)
        self.writeCommands = [] #DESTINATIONNAME|SERVICE|MESSAGE data to send (outb)

    def DefineType(self,connectionNum,input):
        self._activeConnections[int(connectionNum)].data.peerType = input

    def _configureServer(self): #Sets up listener
        self._listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Avoid bind() exception: OSError: [Errno 48] Address already in use
        self._listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listening_socket.bind((self._host, self._port))
        self._listening_socket.listen()

        print(f"{self._type}({self._host},{self._port}): listening on", (self._host, self._port))
        self._listening_socket.setblocking(False)
        self._selector.register(self._listening_socket, selectors.EVENT_READ, data=None) #this only reads in new connections

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        data = types.SimpleNamespace(addr=addr, inb=[], outb=queue.Queue(), peerType="Node", myName=self._connectionNamer)
        conn.setblocking(False)

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        selectorObj = self._selector.register(conn, events, data=data)

        self._activeConnections[self._connectionNamer] = selectorObj #adds the connection at the next available address
        self._connectionNamer += 1 #increment connection namer

    def AppendData(self): #Moves data from writecommands list into the appropriate outb slot
        for NewSend in self.writeCommands:
            x = NewSend.split("|") #splits into array. [0] is the connection
            self._activeConnections[int(x[0])].data.outb.put("|".join(x[1:])) #appends the new data to be sent out

        #TODO this must be cleared safely.
        self.writeCommands.clear()

    def run(self):
        self._configureServer()
        try:
            while True:
                events = self._selector.select(timeout=0.01) #loop every second

                self.CollateData() #collect any inputs from connections
                self.AppendData()  #write any inputs that have been provided by node.py

                for key, mask in events:
                    if key.data is None: #if the key is not initialised
                        self.accept_wrapper(key.fileobj) #add new connection to modules
                    elif mask & selectors.EVENT_READ:
                        self._read(key)
                    elif mask & selectors.EVENT_WRITE and not key.data.outb.empty():
                        self._write(key)
        except KeyboardInterrupt:
            print(f"{self._type}({self._host},{self._port}): caught keyboard interrupt, exiting")
        finally:
            self._selector.close()

    def CollateData(self): #loop through all running connections to get commands and add to outgoing commands list, to be read and processed by Node.py
        for x in self._activeConnections.values():
            #TODO inb needs to become a queue to stop threading issues removing data
            commandsToStore = x.data.inb #get all stored read commands for this connection
            x.data.inb = [] #clear inb of x after aquiring all commands that currently exist
            for y in commandsToStore: #loop through commands
                self.readCommands.append(str(x.data.myName) + "|" + y)


    def ContactNode(self,ConNodeIP,ConNodePort,commands,messageType): #For node to node. messageType = @REG, @REP etc.
        sockVar = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sockVar.connect((ConNodeIP,ConNodePort))

        data = types.SimpleNamespace(addr=(ConNodeIP,ConNodePort), inb=[], outb=queue.Queue(), peerType="Node", myName=str(self._connectionNamer))
        sockVar.setblocking(False)

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        selectorObj = self._selector.register(sockVar, events, data=data)

        newName = self._connectionNamer
        self._activeConnections[self._connectionNamer] = selectorObj #adds the connection at the next available address
        self._connectionNamer += 1 #increment connection namer

        message = messageType + "|" + str(self._type) + "|" + str(self._host) + "|" + str(self._port)

        for x in commands: #Append list of any commands this node can handle, for routing later.
            message += "|" + x

        self.postMessage(newName, message) #Tell parent what IP and Port this node exists on
        return newName #Return the new connection name that has been created

    def _read(self, key):
        packageLen = key.fileobj.recv(10).decode() #Get first 10 characters - defines how long the next part of the packet will be
        if packageLen:
            recv_data = key.fileobj.recv(int(packageLen)).decode()
            print(f"{key.data.peerType}({key.fileobj.getpeername()[0]},{key.fileobj.getpeername()[1]}):", repr(recv_data))
            key.data.inb.append(recv_data)
        if not packageLen:
            print(f"{self._type}({self._host},{self._port}): closing connection on " , repr(key.fileobj.getpeername()))
            self._selector.unregister(key.fileobj)
            key.fileobj.close()

    def _write(self, key):
        try:
            message = key.data.outb.get(False)
        except queue.Empty:
            message = None

        if message == "#":
            pass #Switches to read mode if the output message is the NOOP (#) command
        elif message:
            #Message is sent with readsize

            packetHeader = str(len(message))  # header SMTP defines the response as a server SMTP response as well as the message length
            packetHeaderPadded = f"{packetHeader:<10}"
            packet = packetHeaderPadded + message

            key.fileobj.send(packet.encode())
            print(f"{self._type}({self._host},{self._port}): sent message '{message}' to {key.data.peerType}({key.fileobj.getpeername()[0]},{key.fileobj.getpeername()[1]})")


    def postMessage(self, id, message):
        self._activeConnections[id].data.outb.put(message)