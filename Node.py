"""
Clients are redirected to their service node - data does *not* pass through the control node to external nodes.
Use multiprocessing
"""


import NodeClient
import ThreadHandler

import sys

#Modules
import MODULEHeartbeat
import MODULEEcho
import MODULEDict
import MODULESpawner

class NodeGen():
    def __init__(self,typeParam,parentIP,parentPort):
        self._connectedPort = 0
        self._IP = "127.0.0.1" #TODO modify to allow different IPs
        self._nodeType = typeParam

        self._isPrime = False #first server becomes the prime
        self.encodeFormat = "utf-8"
        self._modules = {}

        self._parentIP = parentIP
        self._parentPort = parentPort
        self._children = []

        self.AppendModules()

    def CreateServer(self,IP,attemptPrime): #Creates a thread listener
        #Prime *always* exists on 51321. Also must be control.
        if attemptPrime is False or self._modules['Heartbeat'].HeartbeatPort(IP,51321): #loads into nonprime location if node does not request prime or if a prime node exists

            self._connectedPort = self._modules['Heartbeat'].FindNextPort(IP, (self._parentPort + 1 if self._parentPort != 0 else 51322)) #Iterates and returns next available port on specified IP
            self._modules['Service'] = ThreadHandler.ThreadHandler(self._nodeType, self._IP, self._connectedPort)
            print(f"Server({self._IP},{self._connectedPort}): initialised on non-prime location ({self._IP}, {self._connectedPort})")

        elif attemptPrime is True:
            self._modules['Service'] = ThreadHandler.ThreadHandler(self._nodeType,IP, 51321)
            self._connectedPort = 51321
            self._isPrime = True
            print(f"Server({self._IP},{self._connectedPort}): initialised on prime location ({self._IP}, {self._connectedPort})")

        self._modules['Service'].start()

        if self._parentPort != 0 and self._parentIP != 0:
            self._modules['Service'].ContactParent(self._parentIP,self._parentPort,self._nodeType) #Send contact info to parent

        self.LoopNode()

    def CreateClient(self): #Autoconnects to prime node
        if self._modules['Heartbeat'].HeartbeatPort("127.0.0.1",51321):
            self._modules['Service'] = NodeClient.NodeClient("Service", self._IP, 51321)
            self._connectedPort = self._modules['Service'].get_port()
            self._modules['Service'].start()
            print(f"Client({self._modules['Service'].get_ip()},{self._modules['Service'].get_port()}): initialised")

            while True:
                request = input("")
                self._modules['Service'].postMessage(request)

        else:
            print(f"Client: prime node does not exist. Client could not be initialised")


    def LoopNode(self): #Initiates infinite loop to repeat actions
        while True:
            if len(self._modules['Service'].readCommands) > 0: #If command exists in read commands buffer
                self._modules['Service'].writeCommands.append(self.CommandParser(self._modules['Service'].readCommands[0])) #Interpret command and return result
                del self._modules['Service'].readCommands[0]

    def run(self): #allows .start()
        pass


    def CommandParser(self,input): #TODO add any error checking to this
        command = input.split("|") #Sender ID,Command,Message

        #Standard should be:
        #Route|Command|Arguments

        if command[1] == "MODULES":
            return command[0] + "|" + str(self._modules.keys())
        elif command[1] == "ECHO" and self._modules.__contains__('Echo'): #checks for command type and if the node has the required module
            return command[0] + "|" + self._modules['Echo'].RequestEcho(command[2]) #return value provided by echo module
        elif command[1] == "ECHODUMP" and self._modules.__contains__('Echo'): #TODO Change this to fit standard
            return command[0] + "|" + self._modules['Echo'].DumpEcho()  # return all echos
        elif command[1] == "CREATE" and self._modules.__contains__('NodeSpawn'): #TODO rework this to take in CREATE types. also allow nodes to decide to create nCodes themselves
            #TODO check for failure?
            print(command[2])
            self._modules['NodeSpawn'].NodeSpawnParse(command[2],self._IP,self._connectedPort) #Spawn node that user requests.
            #TODO make server handle the node spawning
            return command[0] + "|New Node Generated"
        elif command[1] == "DICTADD" and self._modules.__contains__('Dict'): #TODO Change this to fit standard
            self._modules['Dict'].AddToDict(command[2],command[3])  # Add parameter and key to dictionary
            return command[0] + "|Added value to dictionary"
        elif command[1] == "DICT" and self._modules.__contains__('Dict'):
            return command[0] + "|" + self._modules['Dict'].Define(command[2])  # returns value of key
        elif command[1] == "REG":
            self._children.append(NodeChild(command[2],command[3],command[4]))
            print(self._children[0].retValues())
            return command[0] + "|ACK" #TODO this creates an infinite loop. But more importantly, the server to server communications happen on a seperate port... is this correct?
        else:
            return command[0] + "|Unknown command or module does not exist on this node"


    def AppendModules(self): #TODO so far the modules all run on control node, instead of control node making new nodes with modules. change this.
        self._modules['Heartbeat'] = MODULEHeartbeat.HeartbeatModule()

        connectionIP = ("127.0.0.1" if self._parentIP == 0 else str(self._parentIP))

        if self._nodeType == "Control":
            self._modules['Echo'] = MODULEEcho.EchoModule()
            self._modules['NodeSpawn'] = MODULESpawner.SpawnerModule()
            self.CreateServer(connectionIP,True)
        elif self._nodeType == "Client":
            self.CreateClient()
        elif self._nodeType == "Echo":
            self._modules['Echo'] = MODULEEcho.EchoModule()
            self.CreateServer(connectionIP,False)
        elif self._nodeType == "Dictionary":
            self._modules['Dict'] = MODULEDict.DictModule()
            self.CreateServer(connectionIP,False)


class NodeChild():
    def __init__(self,nodeTypeArg,IPArg,PortArg):
        self._nodeType = nodeTypeArg
        self._IP = IPArg
        self._port = PortArg

    def retValues(self):
        return (self._nodeType,self._IP,self._port)


parentIP = 0
parentPort = 0

# print(sys.argv)

if len(sys.argv) > 1:
    nodeRequest = sys.argv[1] #argument 1 defines the node type
    parentIP = sys.argv[2]
    parentPort = int(sys.argv[3])
else:
    nodeRequest = input("Create node:")


NodeGen(nodeRequest,parentIP,parentPort) #spawns up new node of specified type
