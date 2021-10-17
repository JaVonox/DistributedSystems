"""
    A node will represent any item in our distributed system.

    It should be capable of:
        accepting incoming connections on a known port (NodeServer.py)
        processing data from that server (NodeServerThread.py)

        Creating connections to other Servers (NodeClient.py)

        We will likely need specialised variants of these - at the moment they just echo data.

        Tasks:
            Step 1: Create a combined node class that can create servers and clients
            Step 2: The node should default to a known address, checking for the existance of a prime node
            Step 3: If there is a prime node, create a client to server connection to it, register ourselves
            Step 4: Add some kind of functionality to create server/clients on demand
                prime node sends "CREATE SERVER 127.0.0.1 12345"
                prime node sends "CONNECT 127.0.0.1 12345"
                prime node sends "RECONNECT AUTHSERVER 127.0.0.1 12345"
                etc.
            Step 5: Create a few simple specialised node classes e.g.
                echoNode
                pingNode
                etc. (these will later replace their functionality with something sensible)

"""
import NodeClient
import socket

import MODULEReadWrite
import MODULEHeartbeat
import MODULEThreadHandler

class NodeGen:
    def __init__(self,typeParam):
        self._connectedPort = 0
        self._IP = "127.0.0.1"
        self._nodeType = typeParam

        self._isPrime = False #first server becomes the prime
        self.encodeFormat = "utf-8"
        self._modules = {}

        self.AppendModules()

    def CreateServer(self,attemptPrime): #Creates a thread listener
        if attemptPrime is False or self._modules['Heartbeat'].HeartbeatPort("127.0.0.1",51321): #loads into nonprime location if node does not request prime or if a prime node exists
            desiredPort = 51322 #next available port
            while True:
                if self._modules['Heartbeat'].HeartbeatPort("127.0.0.1",desiredPort):
                    desiredPort = desiredPort + 1
                else:
                    self._modules['Service'] = MODULEThreadHandler.ThreadHandler(self._nodeType,self._IP, desiredPort)
                    break
            self._connectedPort = desiredPort
            print(f"Server({self._IP},{self._connectedPort}): initialised on non-prime location ({self._IP}, {self._connectedPort})")
        elif attemptPrime is True:
            self._modules['Service'] = MODULEThreadHandler.ThreadHandler(self._nodeType,"127.0.0.1", 51321)
            self._connectedPort = 51321
            self._isPrime = True
            print(f"Server({self._IP},{self._connectedPort}): initialised on prime location ({self._IP}, {self._connectedPort})")

        self._modules['Service'].start()
        self.LoopNode()

    def CreateClient(self):
        if self._modules['Heartbeat'].HeartbeatPort("127.0.0.1",51321):
            self._modules['Service'] = NodeClient.NodeClient("ConnectingClient", self._IP, 51321)
            self._connectedPort = self._modules['Service'].get_port()
            print(f"Client({self._modules['Service'].get_ip()},{self._modules['Service'].get_port()}): initialised")
            self._modules['Service'].postMessage(f"Hello from client ({self._modules['Service'].get_ip()},{self._modules['Service'].get_port()})!")

            self._modules['Service'].start()
        else:
            print(f"Client: prime node does not exist. Message could not be sent")

    def LoopNode(self): #Initiates infinite loop to repeat actions
        while True:
            if len(self._modules['Service'].readCommands) > 0: #If command exists in read commands buffer
                self._modules['Service'].writeCommands.append(self.CommandParser(self._modules['Service'].readCommands[0])) #Interpret command and return result
                del self._modules['Service'].readCommands[0]

    def CommandParser(self,input):
        command = input.split("|") #Sender ID,Command,Message

        if command[1] == "ECHO":
            return command[0] + "|" + command[2]


    def AppendModules(self):

        self._modules['Heartbeat'] = MODULEHeartbeat.HeartbeatModule()

        if self._nodeType == "Control":
            self.CreateServer(True)
        elif self._nodeType == "Client":
            self.CreateClient()
        elif self._nodeType == "Echo":
            self.CreateServer(False)
        elif self._nodeType == "Dictionary":
            self.CreateServer(False)

