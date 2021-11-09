"""
RESTRICTED VALUES
| SEPERATOR
@ ROUTER TO NON-MODULE FUNCTION
# CALL TO SWITCH TO READ MODE
"""

import ThreadHandler

import sys

#Modules
import MODULEHeartbeat
import MODULEEcho
import MODULEDict
import MODULESpawner

from threading import Thread
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
        self._knownNodes = {} # Thread : NodeData

        self._commandHandlers = {} #command : handler (Self commands)
        self._nodeHandlers = defaultdict(list) #command : [List of known nodes who can handle that command]

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
            print(f"{self._nodeType}({self._IP},{self._connectedPort}): initialised on non-prime location ({self._IP}, {self._connectedPort})")

        elif attemptPrime is True:
            self._modules['Service'] = ThreadHandler.ThreadHandler(self._nodeType,IP, 51321)
            self._connectedPort = 51321
            self._isPrime = True
            print(f"{self._nodeType}({self._IP},{self._connectedPort}): initialised on prime location ({self._IP}, {self._connectedPort})")

        self._modules['Service'].start()

        if self._parentPort != 0 and self._parentIP != 0: #Sends a contact request to the parent node
            self._modules['Service'].ContactNode(self._parentIP,self._parentPort,self._commandHandlers.keys(),"@REG") #Send contact info to parent


    def CreateClient(self,IP): #Autoconnects to prime node
        if self._modules['Heartbeat'].HeartbeatPort("127.0.0.1",51321): #Set up client listening port
            self._connectedPort = self._modules['Heartbeat'].FindNextPort(IP, (self._parentPort + 1 if self._parentPort != 0 else 41322)) #Iterates and returns next available port on specified IP
            self._modules['Service'] = ThreadHandler.ThreadHandler("Client", self._IP, self._connectedPort)
            self._modules['Service'].start()

            print(f"{self._nodeType}({self._IP},{self._connectedPort}): initialised on non-prime location ({self._IP}, {self._connectedPort})")

            print("Command Syntax: COMMAND|PARAMS")

            self._modules['Service'].ContactNode(IP,51321,["NA"],"@REG")
            self._modules['InputReader'] = ClientInputReader() #Starts thread to handle client entering data
            self._modules['InputReader'].start()

            while True:
                if self._modules['InputReader'].ReadFlag(): #If a client has submitted a request
                    tmpInputs = self._modules['InputReader'].ReadRequest()
                    for x in tmpInputs: #append all submitted inputs
                        commands = x.split("|") #Gets the first command
                        route = self.ReturnNodeHandler(commands[0])

                        if route == "#":
                            self._modules['Service'].writeCommands.append("0|" + x)  # 0 is prime node. Default contact.
                        else:
                            self._modules['Service'].writeCommands.append(str(route.RetValues()['Thread']) + "|" + x)  # routed node
                else:
                    self.LoopNode()

        else:
            print(f"{self._nodeType}: prime node does not exist. Client could not be initialised")

    def LoopNode(self): #Initiates infinite loop to repeat actions
        if len(self._modules['Service'].readCommands) > 0: #If command exists in read commands buffer
            self._modules['Service'].writeCommands.append(self.CommandParser(self._modules['Service'].readCommands[0])) #Interpret command and return result
            del self._modules['Service'].readCommands[0]
        pass


    def CommandParser(self,commandInput): #TODO add any error checking to this
        command = commandInput.split("|") #Sender Thread,Command,Message

        #Standard should be:
        #RouteThread|Command|Argument1|Argument2 etc.

        #TODO remove ability for client to send @ manually?
        if command[1][0] == "@": #TODO maybe pack the @ commands into their own module?
            # Builtin Commands (start with @)

            if command[1] == "@REG": #GET REGISTER COMMAND - EXPECT RGE RESPONSE
                newNode = ExtNode(command[2],command[3],command[4],command[0])
                self._modules['Service'].DefineThreadNodeType(command[0],command[2])
                self._knownNodes[command[0]] = newNode
                self.DictCommand(newNode,command[5:]) #add the commands the child can do to a list of commands that a child can process

                #Formats a response to the node to tell it to identify itself
                message = command[0] + "|@RGE|" + self._nodeType + "|" + self._IP + "|" + str(self._connectedPort)
                for x in self._commandHandlers.keys():  # Append list of any commands this node can handle, for routing later.
                    message += "|" + x
                return message

            elif command[1] == "@RGE": #RESPOND TO REGISTER COMMAND - EXPECT ACK RESPONSE
                newNode = ExtNode(command[2], command[3], command[4], command[0])
                self._modules['Service'].DefineThreadNodeType(command[0], command[2])
                self._knownNodes[command[0]] = newNode
                self.DictCommand(newNode,command[5:]) #add the commands the child can do to a list of commands that a child can process

                return command[0] + "|@ACK"

            elif command[1] == "@ACK":
                return command[0] + "|#" #NOOP command

            elif command[1] == "@RED": #This command is sent to a node and tells them to create a new connection with the specified IP/PORT
                newThreadID = self._modules['Service'].ContactNode(command[2], int(command[3]),self._commandHandlers.keys(),"@REG")
                return str(newThreadID) + "|" + self._commandHandlers[command[4]].CommandPoll(command[4],command[5:])

        elif self._nodeType == "Client": #Clients only service @ commands, and will provide no automated response to anything but @ commands
            return command[0] + "|#" #NOOP command

        elif command[1] == "HELP":
            return command[0] + "|Network is currently running the following commands: " + str(",".join(self._commandHandlers.keys())) + ":" + str(",".join(self._nodeHandlers.keys()))

        elif command[1] in self._commandHandlers:
            #Modular Commands
            #directs the command to the handling module
            return command[0] + "|" + self._commandHandlers[command[1]].CommandPoll(command[1],command[2:])

        else:
            #search for node who can process requested command
            foundNode = self.ReturnNodeHandler(command[1])

            #get node of sender - to pass to the handler node
            senderNode = self._knownNodes[command[0]]


            if foundNode == "#":
                return command[0] + "|This command is not available on the network"
            else:
                #Thread that runs the handler + listening ports of requester + initial request of user
                return foundNode.RetValues()["Thread"] + "|@RED|" + str(senderNode.RetValues()["IP"]) + "|" + str(senderNode.RetValues()["Port"]) + "|" + str("|".join(command[1:]))

    def AppendModules(self):
        self._modules['Heartbeat'] = MODULEHeartbeat.HeartbeatModule(self._nodeType)

        connectionIP = ("127.0.0.1" if self._parentIP == 0 else str(self._parentIP))

        if self._nodeType == "Control":
            self._modules['NodeSpawn'] = MODULESpawner.SpawnerModule()
            self.CreateServer(connectionIP,True)
            self._modules['NodeSpawn'].DefineSelf(self._IP, self._connectedPort)  # Set self into spawner
        elif self._nodeType == "Client":
            self.CreateClient(connectionIP)
            pass
        elif self._nodeType == "Echo":
            self._modules['Echo'] = MODULEEcho.EchoModule()
            self.CreateServer(connectionIP,False)
        elif self._nodeType == "Dictionary":
            self._modules['Dict'] = MODULEDict.DictModule()
            self.CreateServer(connectionIP,False)

        while True:
            self.LoopNode()

    def DictCommand(self,child,commandsList): #Creates a dictionary of commands and which known nodes can process said commands
        for x in commandsList:
            if x == "NA": #This is a command from the client - it signifies the client cannot run any commands
                break
            else:
                self._nodeHandlers[x].append(child)

    def ReturnNodeHandler(self,requestedCommand): #Returns the first node that can handle a command
        #TODO modify this to handle case inwhich there is no child with this command - so probably spawn a new one?
        #TODO also this currently only contacts the first spawned child for a command

        if requestedCommand in self._nodeHandlers:
            return self._nodeHandlers[requestedCommand][0]
        else:
            return "#"

class ExtNode():
    def __init__(self,nodeTypeArg,IPArg,PortArg,threadNum):
        self._nodeType = nodeTypeArg
        self._IP = IPArg
        self._port = PortArg
        self._threadNum = threadNum #Thread that handles interactions to this node
        self._commands = []

    def RetValues(self):
        return {"Type" : self._nodeType, "IP" : self._IP, "Port" : self._port, "Thread" : self._threadNum, "Type" : self._nodeType}

    def AddCommand(self,commandName):
        self._commands.append(commandName)

class ClientInputReader(Thread):
    def __init__(self):
        Thread.__init__(self)
        self._requests = []
        self._requestFlag = False #False if no new input, True if new Input

    def ReadRequest(self):
        tmpRequest = self._requests.copy()
        self._requests.clear()
        self._requestFlag = False
        return tmpRequest

    def ReadFlag(self):
        return self._requestFlag

    def run(self): #request input
        while True:
            self._requests.append(input(""))
            self._requestFlag = True

parentIP = 0
parentPort = 0

if len(sys.argv) > 1:
    nodeRequest = sys.argv[1] #argument 1 defines the node type
    parentIP = sys.argv[2]
    parentPort = int(sys.argv[3])
else:
    nodeRequest = input("Create node:")


NodeGen(nodeRequest,parentIP,parentPort) #spawns up new node of specified type
