"""
RESTRICTED VALUES
| SEPERATOR
@ ROUTER TO NON-MODULE FUNCTION
# CALL TO SWITCH TO READ MODE
"""

import ThreadHandler

import sys
import time
import socket

#Modules
import MODULEHeartbeat
import MODULEEcho
import MODULEDict
import MODULESpawner
import MODULEMusic
import MODULEFileSend

from threading import Thread
from collections import defaultdict

class NodeGen():
    def __init__(self,typeParam,parentIP,parentPort,existingIPs):
        self._connectedPort = 0
        self._IP = socket.gethostbyname(socket.gethostname())
        self._nodeType = typeParam

        self.encodeFormat = "utf-8"
        self._modules = {}

        self._parentIP = parentIP
        self._parentPort = parentPort

        self._knownNodes = {} # Thread : NodeData

        self._commandHandlers = {} #command : handler (Self commands)
        self._nodeHandlers = defaultdict(list) #command : [List of known nodes who can handle that command]
        self._heldCommands = [] #holds commands that require a redirect

        self._IPList = existingIPs #Stores all the IPs that can exist. The first one on 51321 is the prime node.

        self.AppendModules()

    def CreateServer(self,IP,attemptBase): #Creates a thread listener

        for x in self._modules.values(): #gets all module classes that can exist
            for y in x.ReturnCommands():
                self._commandHandlers[y] = x
        #Service cannot exist when creating command handlers - it being a module messes things up

        #On 51321 a control node must exist

        if attemptBase is False or self._modules['Heartbeat'].HeartbeatPort(IP,51321): #loads into nonprime location if node does not request prime or if a prime node exists

            self._connectedPort = self._modules['Heartbeat'].FindNextPort(IP, (self._parentPort + 1 if self._parentPort != 0 else 51322)) #Iterates and returns next available port on specified IP
            self._modules['Service'] = ThreadHandler.ThreadHandler(self._nodeType, self._IP, self._connectedPort)

        elif attemptBase is True:
            self._modules['Service'] = ThreadHandler.ThreadHandler(self._nodeType,IP, 51321)
            self._connectedPort = 51321

        print(f"{self._nodeType}({self._IP},{self._connectedPort}): initialised on ({self._IP}, {self._connectedPort})")

        self._modules['Service'].start()

        if self._parentPort != 0 and self._parentIP != 0: #Sends a contact request to the parent node
            self._modules['Service'].ContactNode(self._parentIP,self._parentPort,self._commandHandlers.keys(),"@REG") #Send contact info to parent




    def CreateClient(self): #Autoconnects to prime node

        for x in self._modules.values(): #gets all module classes that can exist
            for y in x.ReturnCommands():
                self._commandHandlers[y] = x

        for IP in self._IPList: #loop through all IPs to find the first that exists

            if self._modules['Heartbeat'].HeartbeatPort(IP,51321): #Set up client listening port
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
                            if self.CheckSelfCommands(x):
                                commands = x.split("|") #Gets the first command
                                route = self.ReturnNodeHandler(commands[0])

                                #TODO allow changing of control node?
                                if route == "#":
                                    self._modules['Service'].writeCommands.append("0|" + x)  # 0 is prime node. Default contact.
                                else:
                                    self._modules['Service'].writeCommands.append(str(route.RetValues()['Thread']) + "|" + x)  # routed node
                    else:
                        self.LoopNode()

        print(f"{self._nodeType}: control node on 51321 does not exist. Client could not be initialised")

    def LoopNode(self): #Initiates infinite loop to repeat actions
        if len(self._modules['Service'].readCommands) > 0: #If command exists in read commands buffer
            self._modules['Service'].writeCommands.append(self.CommandParser(self._modules['Service'].readCommands[0])) #Interpret command and return result
            del self._modules['Service'].readCommands[0]
        if len(self._heldCommands) > 0:
            commandsToKill = []
            for x in self._heldCommands: #this checks if a command is held to be processed - likely a one that would require a DIR response.
                if self.ReturnNodeHandler(x.split("|")[1]) != "#": #check if a handler now exists for this command
                    self._modules['Service'].writeCommands.append(self.CommandParser(x)) #resend the command when a handler spawns
                    commandsToKill.append(self._heldCommands.index(x))

            for y in commandsToKill: #remove all processed commands
                del self._heldCommands[y]
        time.sleep(0.05) #This stops high performance usage without impacting the speed of the system too much
        pass

    def CheckSelfCommands(self,commandInput): #Client only - checks if a command is directed towards a self-owned module.
        command = commandInput.split("|")

        if command[0] in self._commandHandlers.keys():
            self._commandHandlers[command[0]].CommandPoll(command[0], command[1:])
            return False #Owned command - no response required.
        else:
            return True #No owned command


    def CommandParser(self,commandInput):
        command = commandInput.split("|") #Sender Thread,Command,MessageC

        #Standard should be:
        #RouteThread|Command|Argument1|Argument2 etc.
        command = [' ' if a == '' else a for a in command] #replaces all empty commands with a space to stop index errors

        if command[1][0] == "@": #TODO maybe pack the @ commands into their own module?
            # Builtin Commands (start with @). Queries containing @ cannot be manually entered

            if command[1] == "@REG": #GET REGISTER COMMAND - EXPECT REP RESPONSE
                newNode = ExtNode(command[2],command[3],command[4],command[0])
                self._modules['Service'].DefineType(command[0],command[2])
                self._knownNodes[command[0]] = newNode
                self.DictCommand(newNode,command[5:]) #add the commands the child can do to a list of commands that a child can process

                #Formats a response to the node to tell it to identify itself
                message = command[0] + "|@REP|" + self._nodeType + "|" + self._IP + "|" + str(self._connectedPort)
                for x in self._commandHandlers.keys():  # Append list of any commands this node can handle, for routing later.
                    message += "|" + x
                return message

            elif command[1] == "@REP": #RESPOND TO REGISTER COMMAND - EXPECT NO RESPONSE
                newNode = ExtNode(command[2], command[3], command[4], command[0])
                self._modules['Service'].DefineType(command[0], command[2])
                self._knownNodes[command[0]] = newNode
                self.DictCommand(newNode,command[5:]) #add the commands the child can do to a list of commands that a child can process

                return command[0] + "|#"

            elif command[1] == "@DIR": #This command is sent to a node and tells them to create a new connection with the specified IP/PORT
                #Only runs first time a node has to pass a command onwards
                newID = self._modules['Service'].ContactNode(command[2], int(command[3]),self._commandHandlers.keys(),"@REG") #Creates a new REG call
                return self.CommandParser(str(newID) + "|" + command[4] + "|" + str("|".join(command[5:]))) #Calls a recursive command to alleviate issues of writing to the stream too fast

            elif command[1] == "@CLOSED": #If a network connection is closed remove its relevant data from the requested commands
                #Closed should always be received if a connection closes, since the reading node itself will create this request if it loses a connection
                if command[0] in self._knownNodes: #if the id is in the known nodes
                    deadNode = self._knownNodes[command[0]]
                    self.KillNode(deadNode)
                else:
                    pass
                #TODO test with more than one node of same type

            elif command[1] == "@FIL" and self._nodeType == "Client": #this accepts a file as parameters, used for sending music across the network. only accepted by clients
                #This expects the bytes as a hex in command[2], then converts back to bytes
                self._modules['MusicPlayer'].PlayMusic([bytes.fromhex(command[2])])
                return command[0] + "|#"

            return "-1|#"


        elif self._nodeType == "Client": #Clients only service @ commands

            return command[0] + "|#" #NOOP command

        elif command[1] == "HELP":
            return command[0] + "|Network is currently running the following commands: " + str(",".join(self._commandHandlers.keys())) + ":" + str(",".join(self._nodeHandlers.keys()))

        elif command[1] in self._commandHandlers.keys():
            #Modular Commands
            #directs the command to the handling module
            return command[0] + "|" + self._commandHandlers[command[1]].CommandPoll(command[1],command[2:])

        else:
            #search for node who can process requested command
            foundNode = self.ReturnNodeHandler(command[1])

            #get node of sender - to pass to the handler node
            senderNode = self._knownNodes[command[0]]

            if foundNode == "#" and 'NodeSpawn' in self._modules.keys(): #If the module has a nodespawner and the module does not already exist
                nodeSpawn = self._modules['NodeSpawn'].GetCommandHandler(command[1])
                if nodeSpawn != "#":
                    self._modules['NodeSpawn'].Spawn(nodeSpawn)
                    self._heldCommands.append("|".join(command)) #adds the current command to the list of commands that need handling.
                    return command[0] + "|Spawned handler for this command. Please wait for a response."
                else:
                    return command[0] + "|This node does not know the requested command nor any nodes than can handle it"
            if foundNode == "#": #No known node
                return command[0] + "|This node does not know the requested command and lacks the ability to create new nodes"
            else:
                #Thread that runs the handler + listening ports of requester + initial request of user
                #This is run when a user first requests a command that a different node may handle, after this the connections will be client to this node directly
                return foundNode.RetValues()["Thread"] + "|@DIR|" + str(senderNode.RetValues()["IP"]) + "|" + str(senderNode.RetValues()["Port"]) + "|" + str("|".join(command[1:]))

    def AppendModules(self):
        self._modules['Heartbeat'] = MODULEHeartbeat.HeartbeatModule(self._nodeType)

        if self._nodeType == "Control":
            self._modules['NodeSpawn'] = MODULESpawner.SpawnerModule()
            self._modules['NodeSpawn'].AppendSpawnables({"Control","Echo","Dictionary","Distributor"}) #Allow spawning of these nodes
            self.CreateServer(self._IP,True)
            self._modules['NodeSpawn'].DefineSelf(self._IP, self._connectedPort)  # Set self into spawner
        elif self._nodeType == "Client":
            self._modules['MusicPlayer'] = MODULEMusic.MusicModule()
            self._modules['MusicPlayer'].start() #Start the music player, no music is loaded yet though
            self.CreateClient()
            return
        elif self._nodeType == "Echo":
            self._modules['Echo'] = MODULEEcho.EchoModule()
            self.CreateServer(self._IP,False)
        elif self._nodeType == "Dictionary":
            self._modules['Dict'] = MODULEDict.DictModule()
            self.CreateServer(self._IP,False)
        elif self._nodeType == "Distributor":
            self._modules['Distrib'] = MODULEFileSend.DistributorModule()
            self.CreateServer(self._IP,False)
        else:
            print("Invalid node type")
            input("Press any key to continue... ")
            exit()

        while True:
            self.LoopNode() #This is not accessed by the client, which has its own built in loopnode


    def DictCommand(self,node,commandsList): #Creates a dictionary of commands and which known nodes can process said commands
        for x in commandsList:
            if x == "NA": #This is a command from the client - it signifies the client cannot run any commands
                break
            else:
                self._nodeHandlers[x].append(node)

    def ReturnNodeHandler(self,requestedCommand): #Returns the first node that can handle a command
        #TODO also this currently only contacts the first spawned node for a command

        if requestedCommand in self._nodeHandlers:
            return self._nodeHandlers[requestedCommand][0]
        else:
            return "#"

    def KillNode(self,node): #this removes a node that has died from the list of command handlers
        tmpCommands = self._nodeHandlers #all nodes known by this client
        killIndex = []
        for x in tmpCommands:
            if node in tmpCommands[x]:
                del self._nodeHandlers[str(x)][self._nodeHandlers[str(x)].index(node)]
                if len(self._nodeHandlers[str(x)]) == 0: #if there is now no existing handlers
                    killIndex.append(str(x)) #append to the list to kill

        for y in killIndex: #kill all dead commands
            del self._nodeHandlers[str(y)]



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

class ClientInputReader(Thread): #Only used by a client
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
            submittedRequest = input("")
            if "@" in submittedRequest or "#" in submittedRequest:
                print("One or more disallowed characters were detected. Please do not use characters '@' or '#' and resubmit your query")
            else:
                self._requests.append(submittedRequest)
                self._requestFlag = True


def GetConnections():
    #On file is a list of valid IPs. This contains all the IPs the server deems "available" for connection
    #TODO check if node should be prime or listener??
    #On these IPs a node should be running at the port 51321 - the prime
    #TODO add listening node functionality
    #A control node can spawn up new nodes on each IP
    #TODO add this too

    #the client will always try to connect to the first in list on port 51321
    #the server will spawn up a node on 127.0.0.1 regardless of what is on the list
    #the file solely points to which IPs a listener might exist on - if a listener exists on 51321 and is contacted it will spawn up a new node of the requested type
    #This node will then find a port (starting at 51322) and then contact its creator and register itself. The listener should still run on 51321 to expect connections

    f = open("_ConnectionList.txt", "r")
    ValidIPs = f.readlines()
    return ValidIPs

parentIP = 0
parentPort = 0

if len(sys.argv) > 1:
    nodeRequest = sys.argv[1] #argument 1 defines the node type
    parentIP = sys.argv[2]
    parentPort = int(sys.argv[3])
else:
    nodeRequest = input("Create node: ")

NodeGen(nodeRequest,parentIP,parentPort,GetConnections()) #spawns up new node of specified type
