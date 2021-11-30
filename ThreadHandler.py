import socket
import selectors
import types
import queue
import time
from threading import Thread

#list of commands to not print when sent/recieved and what should be printed instead.
#These commands are used too often and clog up space in the console. So its not worth it to show the print
#This applies to clients only
ignoredCommands = [
    "@REG",
    "@REP",
    "@DIR",
    "@FIL"
]
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
        self._configureServer()

    def DefineType(self,connectionNum,input):
        self._activeConnections[int(connectionNum)].data.peerType = input

    def _configureServer(self): #Sets up listener
        self._listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Avoid bind() exception: OSError: [Errno 48] Address already in use
        self._listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listening_socket.bind((self._host, self._port))
        self._listening_socket.listen()

        print(f"{self._type}({self._host},{self._port}): listening on", (self._host, self._port))
        self._listening_socket.setblocking(True)
        self._selector.register(self._listening_socket, selectors.EVENT_READ, data=None) #this only reads in new connections

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        data = types.SimpleNamespace(addr=addr, inb=[], outb=queue.Queue(), peerType="Node", myName=self._connectionNamer,unfinRead="", readExplen=0, initExplen=0, lastPrint=10)
        conn.setblocking(True)

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        selectorObj = self._selector.register(conn, events, data=data)

        self._activeConnections[self._connectionNamer] = selectorObj #adds the connection at the next available address
        self._connectionNamer += 1 #increment connection namer

    def AppendData(self): #Moves data from writecommands list into the appropriate outb slot
        for NewSend in self.writeCommands:
            x = NewSend.split("|") #splits into array. [0] is the connection
            if int(x[0]) != -1: #-1 is the code for a connection that does not exist anymore
                self._activeConnections[int(x[0])].data.outb.put("|".join(x[1:])) #appends the new data to be sent out

        self.writeCommands.clear()

    def run(self):
        while True:
            events = self._selector.select(timeout=0)

            self.CollateData() #collect any inputs from connections
            self.AppendData()  #write any inputs that have been provided by node.py

            for key, mask in events:
                if key.data is None: #if the key is not initialised
                    self.accept_wrapper(key.fileobj) #add new connection to modules
                elif mask & selectors.EVENT_READ or key.data.readExplen != 0: #if the node is expecting a read or has pending data output
                    self._read(key)
                elif mask & selectors.EVENT_WRITE and not key.data.outb.empty():
                    self._write(key)
            time.sleep(0.05) #This stops high performance usage without impacting the speed of the system too much

    def KillConnection(self,key):
        del self._activeConnections[int(key.data.myName)]
        self._selector.unregister(key.fileobj)
        key.fileobj.close()

    def KillFromID(self,id):
        if id in self._activeConnections.keys():
            self.KillConnection(id)
        else: #This occurs when a request such as a heartbeat is found - so one that doesnt have an active connection
            pass

    def CollateData(self): #loop through all running connections to get commands and add to outgoing commands list, to be read and processed by Node.py
        for x in self._activeConnections.values():
            commandsToStore = x.data.inb #get all stored read commands for this connection
            x.data.inb = [] #clear inb of x after aquiring all commands that currently exist
            for y in commandsToStore: #loop through commands
                self.readCommands.append(str(x.data.myName) + "|" + y)


    def ContactNode(self,ConNodeIP,ConNodePort,Load,arguments,messageType): #For node to node. messageType = @REG, @REP etc.
        sockVar = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sockVar.connect((ConNodeIP,ConNodePort))

        data = types.SimpleNamespace(addr=(ConNodeIP,ConNodePort), inb=[], outb=queue.Queue(), peerType="Node", myName=str(self._connectionNamer), unfinRead="", readExplen=0, initExplen=0, lastPrint=10)
        sockVar.setblocking(True)

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        selectorObj = self._selector.register(sockVar, events, data=data)

        newName = self._connectionNamer
        self._activeConnections[self._connectionNamer] = selectorObj #adds the connection at the next available address
        self._connectionNamer += 1 #increment connection namer

        if messageType != "NULL":
            message = messageType + "|" + str(self._type) + "|" + str(self._host) + "|" + str(self._port) + "|" + str(Load)

            for x in arguments: #Append list of any commands this node can handle, for routing later.
                message += "|" + x
        else:
            message = arguments #When given the NULL command, the arguments are expected as a string and will be sent as is

        self.postMessage(newName, message) #Tell parent what IP and Port this node exists on
        return newName #Return the new connection name that has been created


    def _read(self, key):
        try:
            if key.data.readExplen == 0: #If this is the start of the string
                key.data.readExplen = int(key.fileobj.recv(25).decode()) #Get first 25 characters - defines how long the next part of the packet will be
                key.data.initExplen = key.data.readExplen #store initial explen
                if(key.data.readExplen >= 1024): #if there is a lot of data to send
                    print(f"{self._type}({self._host},{self._port}): Downloading a lot of data... please wait...")
            else:
                pass

            recv_data = key.fileobj.recv(int(key.data.readExplen)).decode()

            if(len(recv_data) < key.data.readExplen): #waits if the full packet has not been recieved
                key.data.unfinRead += recv_data
                key.data.readExplen -= len(recv_data)

                #if greater than the percentage last progress printed at (default 10)
                if float(key.data.initExplen - key.data.readExplen) / float(key.data.initExplen) * 100 > float(key.data.lastPrint):
                    print("Downloading... (" + str(round((float(key.data.initExplen - key.data.readExplen) / float(key.data.initExplen)* 100))) + "%)") #Print progress
                    key.data.lastPrint += 10

            else:
                dataOut = key.data.unfinRead + recv_data

                #reset data
                key.data.unfinRead = ""
                key.data.readExplen = 0
                key.data.lastPrint = 10
                key.data.inb.append(dataOut)

                if dataOut.split("|")[0] in ignoredCommands and self._type == "Client": #this stops the client printing data that it doesnt require
                    pass
                else:
                    print(f"{key.data.peerType}({key.fileobj.getpeername()[0]},{key.fileobj.getpeername()[1]}):", repr(recv_data))
        except Exception as e: #if an error occurs when attempting to read the package (likely a closed port)
            if key.data.peerType != "Node": #Should eliminate most heartbeat requests from being printed
                print(f"{self._type}({self._host},{self._port}): connection closed by {key.data.peerType}{repr(key.fileobj.getpeername())}")
            self.readCommands.append(str(key.data.myName) + "|@CLOSED") #Manually add to readcommands, since the connection will not be active in a second
            self.KillConnection(key)

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
            packetHeaderPadded = f"{packetHeader:<25}"
            packet = packetHeaderPadded + message

            key.fileobj.send(packet.encode())

            if message.split("|")[0] in ignoredCommands and self._type == "Client": #this stops the client printing data that it doesnt require
                pass
            else:
                if(len(message) >= 500):
                    print(f"{self._type}({self._host},{self._port}): sent message of length '{len(message)}' ({message[:15]}...) to {key.data.peerType}({key.fileobj.getpeername()[0]},{key.fileobj.getpeername()[1]})")
                else:
                    print(f"{self._type}({self._host},{self._port}): sent message '{message}' to {key.data.peerType}({key.fileobj.getpeername()[0]},{key.fileobj.getpeername()[1]})")


    def postMessage(self, id, message):
        self._activeConnections[id].data.outb.put(message)