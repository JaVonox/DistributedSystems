"""
Clients are redirected to their service node - data does *not* pass through the control node to external nodes.
Use multiprocessing
"""


import NodeClient
import ThreadHandler
import subprocess

import sys

#Modules
import MODULEHeartbeat
import MODULEEcho
import MODULEDict

class NodeGen():
    def __init__(self,typeParam):
        self._connectedPort = 0
        self._IP = "127.0.0.1"
        self._nodeType = typeParam

        self._isPrime = False #first server becomes the prime
        self.encodeFormat = "utf-8"
        self._modules = {}

        self.AppendModules()


    #TODO Add ability to make new nodes. These should be initialised with required modules (including service module which should handle its events and read/write)
    def CreateServer(self,attemptPrime): #Creates a thread listener
        if attemptPrime is False or self._modules['Heartbeat'].HeartbeatPort("127.0.0.1",51321): #loads into nonprime location if node does not request prime or if a prime node exists
            desiredPort = 51322 #next available port
            while True:
                if self._modules['Heartbeat'].HeartbeatPort("127.0.0.1",desiredPort):
                    desiredPort = desiredPort + 1
                else:
                    self._modules['Service'] = ThreadHandler.ThreadHandler(self._nodeType,self._IP, desiredPort)
                    break
            self._connectedPort = desiredPort
            print(f"Server({self._IP},{self._connectedPort}): initialised on non-prime location ({self._IP}, {self._connectedPort})")
        elif attemptPrime is True:
            self._modules['Service'] = ThreadHandler.ThreadHandler(self._nodeType,"127.0.0.1", 51321)
            self._connectedPort = 51321
            self._isPrime = True
            print(f"Server({self._IP},{self._connectedPort}): initialised on prime location ({self._IP}, {self._connectedPort})")

        self._modules['Service'].start()
        self.LoopNode()

    def CreateClient(self): #Autoconnects to prime node
        if self._modules['Heartbeat'].HeartbeatPort("127.0.0.1",51321):
            self._modules['Service'] = NodeClient.NodeClient("ConnectingClient", self._IP, 51321)
            self._connectedPort = self._modules['Service'].get_port()
            self._modules['Service'].start()
            print(f"Client({self._modules['Service'].get_ip()},{self._modules['Service'].get_port()}): initialised")

            while True:
                request = input("")
                self._modules['Service'].postMessage(request)

        else:
            print(f"Client: prime node does not exist. Message could not be sent")

    def LoopNode(self): #Initiates infinite loop to repeat actions
        while True:
            if len(self._modules['Service'].readCommands) > 0: #If command exists in read commands buffer
                self._modules['Service'].writeCommands.append(self.CommandParser(self._modules['Service'].readCommands[0])) #Interpret command and return result
                del self._modules['Service'].readCommands[0]

    def run(self): #allows .start()
        pass


    def CommandParser(self,input): #TODO add any error checking to this
        command = input.split("|") #Sender ID,Command,Message

        if command[1] == "MODULES":
            return command[0] + "|" + str(self._modules.keys())
        elif command[1] == "ECHO" and self._modules.__contains__('Echo'): #checks for command type and if the node has the required module
            return command[0] + "|" + self._modules['Echo'].RequestEcho(command[2]) #return value provided by echo module
        elif command[1] == "ECHODUMP" and self._modules.__contains__('Echo'):
            return command[0] + "|" + self._modules['Echo'].DumpEcho()  # return all echos
        elif command[1] == "CREATE" and self._modules.__contains__('NodeSpawn'): #TODO rework this to take in CREATE types. also allow nodes to decide to create nodes themselves
            #TODO check for failure?
            subprocess.Popen(['python', 'Node.py','Control'],creationflags=subprocess.CREATE_NEW_CONSOLE) #subprocessing based node generation. Adds argument control to define node type to generate
            return command[0] + "|New Control Node Generated"
        elif command[1] == "DICTADD" and self._modules.__contains__('Dict'):
            self._modules['Dict'].AddToDict(command[2],command[3])  # Add parameter and key to dictionary
            return command[0] + "|Added value to dictionary"
        elif command[1] == "DICT" and self._modules.__contains__('Dict'):
            return command[0] + "|" + self._modules['Dict'].Define(command[2])  # returns value of key
        else:
            return command[0] + "|Unknown command or module does not exist on this node"


    def AppendModules(self): #TODO so far the modules all run on control node, instead of control node making new nodes with modules. change this.
        self._modules['Heartbeat'] = MODULEHeartbeat.HeartbeatModule()

        if self._nodeType == "Control":
            self._modules['Echo'] = MODULEEcho.EchoModule()
            self._modules['Dict'] = MODULEDict.DictModule()
            self._modules['NodeSpawn'] = MODULEDict.DictModule() #TODO temp module
            self.CreateServer(True)
        elif self._nodeType == "Client":
            self.CreateClient()
        elif self._nodeType == "Echo":
            self.CreateServer(False)
        elif self._nodeType == "Dictionary":
            self.CreateServer(False)

def GenerateNewNode(nodeType):
    NodeGen(nodeType) #spawns up new node of specified type

print(str(sys.argv))
if len(sys.argv) > 1:
    nodeRequest = sys.argv[1] #argument 1 defines the node type
else:
    nodeRequest = input("Create node:")

if nodeRequest == "Control":
    GenerateNewNode("Control")
elif nodeRequest == "Client":
    GenerateNewNode("Client")
elif nodeRequest == "Echo":
    GenerateNewNode("Echo")