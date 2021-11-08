"""
RESTRICTED VALUES
| SEPERATOR
@ ROUTER TO NON-MODULE FUNCTION
# CALL TO SWITCH TO READ MODE
"""


import NodeClient
import ThreadHandler

import sys

#Modules
import MODULEHeartbeat
import MODULEEcho
import MODULEDict
import MODULESpawner

from collections import defaultdict

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

        self._commandHandlers = {} #command : handler
        self._childHandlers = defaultdict(list) #command : [List of children who can handle that command]

        self.AppendModules()

    def CreateServer(self,IP,attemptPrime): #Creates a thread listener

        for x in self._modules.values(): #gets all module classes
            for y in x.ReturnCommands():
                self._commandHandlers[y] = x
        #Service cannot exist when creating command handlers - it being a module messes things up

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

        if self._parentPort != 0 and self._parentIP != 0: #Sends a contact request to the parent node
            self._modules['Service'].ContactParent(self._parentIP,self._parentPort,self._nodeType,self._commandHandlers.keys()) #Send contact info to parent


    def CreateClient(self): #Autoconnects to prime node
        if self._modules['Heartbeat'].HeartbeatPort("127.0.0.1",51321):
            self._modules['Client'] = NodeClient.NodeClient("Client", self._IP, 51321)
            self._connectedPort = self._modules['Client'].get_port()
            self._modules['Client'].start()

            print(f"Client({self._modules['Client'].get_ip()},{self._modules['Client'].get_port()}): initialised")

            while True:
                request = input("")
                self._modules['Client'].postMessage(request)

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
        #RouteThread|Command|Argument1|Argument2 etc.

        #TODO remove ability for client to send @ manually?
        if command[1][0] == "@": #TODO maybe pack the @ commands into their own module?
            # Builtin Commands (start with @)
            if command[1] == "@REG":
                newChild = NodeChild(command[2],command[3],command[4],command[0])
                self._children.append(newChild)
                self.AddChildCommands(newChild,command[5:]) #add the commands the child can do to a list of commands that a child can process
                return command[0] + "|@ACK"
            elif command[1] == "@ACK":
                return command[0] + "|#" #NOOP command
            elif command[1] == "@RED": #This command is sent to a child and tells them to create a new connection with the specified IP/PORT, then send the results of an operation
                #TODO May need reworking?
                #Sends message to client with response data
                self._modules['Service'].Contact(str(command[2]),int(command[3]),self._commandHandlers[command[4]].CommandPoll(command[4],command[5:]))
        elif command[1] == "HELP":
            return command[0] + "|Network is currently running the following commands: " + str(",".join(self._commandHandlers.keys())) + ":" + str(",".join(self._childHandlers.keys()))
        elif command[1] in self._commandHandlers:
            #Modular Commands
            #directs the command to the handling module
            return command[0] + "|" + self._commandHandlers[command[1]].CommandPoll(command[1],command[2:])
        else:
            #search for child who can process requested command
            child = self.ReturnChildWithCommand(command[1])
            responseAddress = self._modules['Service'].GetThreadInfo(command[0])

            if child == 0:
                return command[0] + "|This command is not available on the network"
            else:
                return child.RetValues()["Thread"] + "|@RED|" + str(responseAddress[0]) + "|" + str(responseAddress[1]) + "|" + "|".join(command[1:])


    def AppendModules(self):
        self._modules['Heartbeat'] = MODULEHeartbeat.HeartbeatModule()

        connectionIP = ("127.0.0.1" if self._parentIP == 0 else str(self._parentIP))

        if self._nodeType == "Control":

            self._modules['NodeSpawn'] = MODULESpawner.SpawnerModule()

            self._modules['Dict'] = MODULEDict.DictModule()
            self.CreateServer(connectionIP,True)

            self._modules['NodeSpawn'].DefineSelf(self._IP, self._connectedPort)  # Set self into spawner
        elif self._nodeType == "Client":
            self.CreateClient()
            pass
        elif self._nodeType == "Echo":
            self._modules['Echo'] = MODULEEcho.EchoModule()
            self.CreateServer(connectionIP,False)
        elif self._nodeType == "Dictionary":
            self._modules['Dict'] = MODULEDict.DictModule()
            self.CreateServer(connectionIP,False)

        self.LoopNode()

    def AddChildCommands(self,child,commandsList): #Creates a dictionary of commands and which children can process said commands
        for x in commandsList:
            self._childHandlers[x].append(child)



    def ReturnChildWithCommand(self,requestedCommand):
        #TODO modify this to handle case inwhich there is no child with this command - so probably spawn a new one?
        #TODO also this currently only contacts the first spawned child for a command

        if requestedCommand in self._childHandlers:
            return self._childHandlers[requestedCommand][0]
        else:
            return 0




class NodeChild():
    def __init__(self,nodeTypeArg,IPArg,PortArg,threadNum):
        self._nodeType = nodeTypeArg
        self._IP = IPArg
        self._port = PortArg
        self._threadNum = threadNum

    def RetValues(self):
        return {"Type" : self._nodeType, "IP" : self._IP, "Port" : self._port, "Thread" : self._threadNum}

    def RetType(self):
        return self._nodeType


parentIP = 0
parentPort = 0

if len(sys.argv) > 1:
    nodeRequest = sys.argv[1] #argument 1 defines the node type
    parentIP = sys.argv[2]
    parentPort = int(sys.argv[3])
else:
    nodeRequest = input("Create node:")


NodeGen(nodeRequest,parentIP,parentPort) #spawns up new node of specified type
