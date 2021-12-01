"""
RESTRICTED VALUES
| SEPERATOR
@ ROUTER TO NON-MODULE FUNCTION
* ROUTER TO LOAD BALANCING
# CALL TO SWITCH TO READ MODE
"""

import ThreadHandler

import sys
import time
import socket

#Modules
from Modules import MODULEHeartbeat
from Modules import MODULEEcho
from Modules import MODULEDict
from Modules import MODULESpawner
from Modules import MODULEMusic
from Modules import MODULEFileSend
from Modules import MODULELoadBalancer
from Modules import MODULELoadReporter

from threading import Thread
from collections import defaultdict

class NodeGen():
    def __init__(self,typeParam,parentIP,parentPort,existingIPs,myIP):
        self._connectedPort = 0
        self._IP = myIP
        self._nodeType = typeParam

        self.encodeFormat = "utf-8"
        self._modules = {}

        self._parentIP = parentIP
        self._parentPort = parentPort

        self._knownNodes = {} # Socket Address : NodeData

        self._commandHandlers = {} #command : handler (Self commands)
        self._nodeHandlers = defaultdict(list) #command : [List of known nodes who can handle that command (in EXTNODE format)]
        self._heldCommands = [] #holds commands that require a redirect

        self._IPList = existingIPs #Stores all the IPs that can exist. The first one on 50001 is the prime node.
        self.AppendModules()

    #TODO due to the limited ports in the lab add error checking to ensure port is between 50001 and 50010. 50001-50006 are nodes, 50006-50009 are clients
    def CreateServer(self,IP,attemptBase): #Creates a thread listener

        for x in self._modules.values(): #gets all module classes that can exist on this node
            for y in x.ReturnCommands():
                self._commandHandlers[y] = x
        #Service cannot exist when creating command handlers - it being a module messes things up

        #On 50001 a control node must exist

        if attemptBase is False or self._modules['Heartbeat'].HeartbeatPort(IP,50001): #loads into nonprime location if node does not request prime or if a prime node exists

            self._connectedPort = self._modules['Heartbeat'].FindNextPort(IP, (self._parentPort + 1 if self._parentPort != 0 else 50002)) #Iterates and returns next available port on specified IP
            self._modules['Service'] = ThreadHandler.ThreadHandler(self._nodeType, self._IP, self._connectedPort)

        elif attemptBase is True: #TODO this might cause problems if two or more control nodes exist on a single connection
            self._modules['Service'] = ThreadHandler.ThreadHandler(self._nodeType,IP, 50001)
            self._connectedPort = 50001

        print(f"{self._nodeType}({self._IP},{self._connectedPort}): initialised on ({self._IP}, {self._connectedPort})")

        self._modules['Service'].start()

        if self._parentPort != 0 and self._parentIP != 0: #Sends a contact request to the parent node
            self._modules['Service'].ContactNode(self._parentIP,self._parentPort,self._modules['LoadRep'].ReturnLoad({""}),self._commandHandlers.keys(),"@REG") #Send contact info to parent

    def CreateClient(self): #Autoconnects to prime node

        for x in self._modules.values(): #gets all module classes that can exist
            for y in x.ReturnCommands():
                self._commandHandlers[y] = x

        for IP in self._IPList: #loop through all IPs to find the first that exists

            if self._modules['Heartbeat'].HeartbeatPort(IP,50001): #Set up client listening port
                print("Found server. Connecting...")
                self._connectedPort = self._modules['Heartbeat'].FindNextPort(self._IP, 50006) #Iterates and returns next available port on specified IP
                self._modules['Service'] = ThreadHandler.ThreadHandler("Client", self._IP, self._connectedPort)
                self._modules['Service'].start()

                print(f"{self._nodeType}({self._IP},{self._connectedPort}): initialised on non-prime location ({self._IP}, {self._connectedPort})")
                print("Command Syntax: COMMAND|PARAMS")

                self._modules['Service'].ContactNode(IP,50001,"NA",["NA"],"@REG")
                self._modules['InputReader'] = ClientInputReader() #Starts thread to handle client entering data
                self._modules['InputReader'].start()

                while True:
                    if self._modules['InputReader'].ReadFlag(): #If a client has submitted a request
                        tmpInputs = self._modules['InputReader'].ReadRequest()
                        for x in tmpInputs: #append all submitted inputs
                            if self.CheckSelfCommands(x):
                                commands = x.split("|") #Gets the first command
                                route = self.ReturnNodeHandler(commands[0]) #return the thread of the handler

                                #TODO allow changing of control node?
                                if route == "#":
                                    self._modules['Service'].writeCommands.append("0|" + x)  # 0 is prime node. Default contact.
                                else:
                                    self._modules['Service'].writeCommands.append(str(route) + "|" + x)  # routed node
                    else:
                        self.LoopNode()

        print(f"{self._nodeType}: control node on 50001 does not exist. Client could not be initialised")

    def LoopNode(self): #Initiates infinite loop to repeat actions
        if len(self._modules['Service'].readCommands) > 0: #If command exists in read commands buffer
            self._modules['Service'].writeCommands.append(self.CommandParser(self._modules['Service'].readCommands[0])) #Interpret command and return result
            del self._modules['Service'].readCommands[0]
        if len(self._heldCommands) > 0:
            commandsToKill = []
            for x in self._heldCommands: #this checks if a command is held to be processed - likely a one that would require a DIR response.
                if self.ReturnNodeHandler(x.split("|")[1]) != "#" and x.split("|")[0] in self._knownNodes: #check if a handler now exists for this command and the recipient is in the list of known nodes
                    self._modules['Service'].writeCommands.append(self.CommandParser(x)) #resend the command when a handler spawns
                    commandsToKill.append(self._heldCommands.index(x))

            for y in commandsToKill: #remove all processed commands
                del self._heldCommands[y]
        if "LoadRep" in self._modules:
            clients=0
            for a in self._knownNodes.values():
                if(a.RetValues()["Type"] == "Client"):
                    clients+=1
            needUpdate = self._modules['LoadRep'].UpdateLoad(clients)

            if needUpdate == 1 and "LoadBal" not in self._modules: #when a node value changes but the node does not have a node balancing module
                #Report change in balance to parent. Each node should only have *one* known control node unless it is a control node itself
                #TODO make nodes shutdown if they no longer know a control node
                threadOfParent = "" #finds the thread of the parent
                for b in self._knownNodes.values():
                    if(b.RetValues()["Type"] == "Control"):
                        threadOfParent = str(b.RetValues()["Thread"])
                        break
                message = str(threadOfParent) + "|*LOADUPDATE|" + self._IP + "|" + str(self._connectedPort) + "|" + str(clients) #message to send to parent to update their load balancing dataset

                self._modules['Service'].writeCommands.append(message) #This does not need to go through command parser because it is already a complete command
        if "LoadBal" in self._modules: #updates the checks to see if any new nodes can be spawned on this IP
            clients=0
            for a in self._knownNodes.values():
                if(a.RetValues()["Type"] == "Client"): #checks number of active client connections on this IP
                    clients +=1

            self._modules["LoadBal"].UpdateSelfLoadFlag(clients) #update the system to check if the requested number of clients has been reached
            self._modules["NodeSpawn"].UpdateRedir = not self._modules["LoadBal"].GetNewNodeNeeded() #the spawner is set to accept new redirects if the IP is not full

            for clientToHandle in self._modules['LoadBal'].addressesNeedingRedirect: #check the amount of active redirect requests and append the written command to the output for each
                #clientToHandle is tuple - (IP,PORT,Iteration) Where iteration is the next IP to contact in the list of active IPs.
                self.EstablishControlNetwork()
                pass

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

            #this ensures the client reports its load as NA but other nodes report the correct load
            selfload = "NA"
            if "LoadRep" in self._modules:
                selfload = str(self._modules['LoadRep'].ReturnLoad({""}))

            if command[1] == "@REG": #GET REGISTER COMMAND - EXPECT REP RESPONSE

                if "LoadBal" in self._modules and str(command[2]) == "Client":
                    if self._modules["LoadBal"].GetNewNodeNeeded(): #If this client needs a new control node redirect
                        self._modules["LoadBal"].addressesNeedingRedirect.append((command[3],command[4],0)) #adds the element to the list of items needing redirect
                        #Tuple is the IP, the port and the current ID of the IP to request a slot from.
                        #TODO left off here

                        """
                        So it currently stores the IP and port of a client needing a redirect
                        This should then be sent around to the known control nodes one at a time - which perhaps the control node should contact at the start of the system runtime??
                        If the other control responds with a positive request, the node assumes it has made the connection and breaks connection
                        If the other control, we move onto the next in the list
                        
                        Starting off by contacting all other nodes wont work because that would assume they all existed simultaneously
                        """

                        return command[0] + "|@NOSPACE" #send client data that no space is available, this causes them to kill their connection and expect a new one

                newNode = ExtNode(command[2],command[3],command[4],command[0])
                self._modules['Service'].DefineType(command[0],command[2])
                self._knownNodes[command[0]] = newNode
                self.DictCommand(newNode,command[6:]) #add the commands the child can do to a list of commands that a child can process

                if "LoadBal" in self._modules: #if this module can load balance, add the node data into the load balancer
                    self._modules["LoadBal"].RegisterLoad(command[0],command[5]) #append node load

                #Formats a response to the node to tell it to identify itself
                message = command[0] + "|@REP|" + self._nodeType + "|" + self._IP + "|" + str(self._connectedPort) + "|" + selfload
                for x in self._commandHandlers.keys():  # Append list of any commands this node can handle, for routing later.
                    message += "|" + x

                return message

            elif command[1] == "@REP": #RESPOND TO REGISTER COMMAND - EXPECT NO RESPONSE
                newNode = ExtNode(command[2], command[3], command[4], command[0])
                self._modules['Service'].DefineType(command[0], command[2])
                self._knownNodes[command[0]] = newNode

                if "LoadBal" in self._modules: #if this module can load balance, add the node data into the load balancer
                    self._modules["LoadBal"].RegisterLoad(command[0],command[5]) #append node load

                self.DictCommand(newNode,command[6:]) #add the commands the child can do to a list of commands that a child can process
                return command[0] + "|#"

            elif command[1] == "@DIR": #This command is sent to a node and tells them to create a new connection with the specified IP/PORT
                #Only runs first time a node has to pass a command onwards
                newID = self._modules['Service'].ContactNode(command[2], int(command[3]),selfload,self._commandHandlers.keys(),"@REG") #Creates a new REG call
                return self.CommandParser(str(newID) + "|" + command[4] + "|" + str("|".join(command[5:]))) #Calls a recursive command to alleviate issues of writing to the stream too fast

            elif command[1] == "@CLOSED": #If a network connection is closed remove its relevant data from the requested commands
                #Closed should always be received if a connection closes, since the reading node itself will create this request if it loses a connection
                if command[0] in self._knownNodes: #if the id is in the known nodes
                    deadNode = self._knownNodes[command[0]]
                    self.KillNode(deadNode)
                    del self._knownNodes[command[0]] #remove node from list of nodes

                    if "LoadBal" in self._modules:
                        self._modules["LoadBal"].KillThread(command[0])

                return "-1|#"

            elif command[1] == "@NOSPACE": #This tells a client that there is no space on this control and to expect a redirect
                #TODO wait until a new control contacts the client, then close the original connection when required.
                print("This server is currently overloaded, please wait for a redirect...")
                self._modules["Service"].KillFromID(command[0]) #closes the server/client connection

                if command[0] in self._knownNodes: #if the id is in the known nodes
                    deadNode = self._knownNodes[command[0]]
                    self.KillNode(deadNode)
                    del self._knownNodes[command[0]] #remove node from list of nodes

                    if "LoadBal" in self._modules:
                        self._modules["LoadBal"].KillThread(command[0])

                return "-1|#" #ending the stream

            elif command[1] == "@FIL" and self._nodeType == "Client": #this accepts a file as parameters, used for sending music across the network. only accepted by clients
                #This expects the bytes as a hex in command[2], then converts back to bytes
                self._modules['MusicPlayer'].PlayMusic([bytes.fromhex(command[2])])
                return command[0] + "|#"


        elif self._nodeType == "Client": #Clients only service @ commands
            return command[0] + "|#" #NOOP command

        elif command[1] == "HELP":
            #TODO remove * commands from this list
            return command[0] + "|Network is currently running the following commands: " + str(",".join(self._commandHandlers.keys())) + ":" + str(",".join(self._nodeHandlers.keys()))

        elif command[1] in self._commandHandlers.keys():
            #Modular Commands
            #directs the command to the handling module on this node
            return command[0] + "|" + self._commandHandlers[command[1]].CommandPoll(command[1],command[2:],command[0])

        else:

            #search for thread of node that can use this command
            foundNode = self.ReturnNodeHandler(command[1])

            # get node of sender - to pass to the handler node
            senderNode = None
            if int(command[0]) in self._knownNodes:
                senderNode = self._knownNodes[command[0]]
            else:
                #Forces the system to wait until the sender has been registered - This prevents issues where DIR would attempt to fire before client response
                self._heldCommands.append("|".join(command))
                #TODO error occurs here when a second client tries to connect to the redirected server.
                #TODO to clarify - the foreign control node can spawn up multiple new nodes, but cant handle connections from more than one client as of yet.

            if foundNode == "#" and 'NodeSpawn' in self._modules.keys(): #If the module has a nodespawner and the module does not already exist
                nodeSpawn = self._modules['NodeSpawn'].GetCommandHandler(command[1])
                if nodeSpawn != "#":
                    self._modules['NodeSpawn'].Spawn(nodeSpawn)
                    if not "|".join(command) in self._heldCommands: #Prevents a bug where the request would be appended twice
                        self._heldCommands.append("|".join(command)) #adds the current command to the list of commands that need handling.
                    return command[0] + "|Spawned handler for this command. Please wait for a response."
                else:
                    return command[0] + "|This node does not know the requested command nor any nodes than can handle it"
            if foundNode == "#": #No known node
                return command[0] + "|This node does not know the requested command and lacks the ability to create new nodes"
            else:

                #Thread that runs the handler + listening ports of requester + initial request of user
                #This is run when a user first requests a command that a different node may handle, after this the connections will be client to this node directly
                return foundNode + "|@DIR|" + str(senderNode.RetValues()["IP"]) + "|" + str(senderNode.RetValues()["Port"]) + "|" + str("|".join(command[1:]))

    def EstablishControlNetwork(self): #This sends a contact request to all listed controls in the IP list - skipping those that an active connection already exists for.
        #This is only used by control nodes
        #TODO check for non control accessors
        KnownControls = []

        for a in self._knownNodes.values(): #iterate through all known nodes
            if a.RetValues()["Type"] == "Control" or a.RetValues()["IP"] in self._modules['LoadBal'].pingedControlIPs:
                KnownControls = a.RetValues()["IP"] #adds the IPs to the list of known IPs with active connections

        for x in self._IPList:
            if x in KnownControls or x == self._IP: #check if this IP is in the set of known IPs
                #TODO maybe do heartbeat here??
                pass
            else:
                #Create a REG connection to all uncontacted control nodes
                #TODO handle heartbeat failure???
                #TODO this might overload the system if there isnt a cooldown
                if self._modules['Heartbeat'].HeartbeatPort(x,50001): #Check if a control exists on the specified location
                    self._modules['LoadBal'].pingedControlIPs.append(x) #adds to known controls to stop repeat calls
                    self._modules['Service'].ContactNode(x, 50001,"NA","CTRL","@REG") #Creates a new REG call to the uncontacted control node
        pass

    def AppendModules(self):
        self._modules['Heartbeat'] = MODULEHeartbeat.HeartbeatModule(self._nodeType) #appends to all nodes

        if self._nodeType == "Client":
            self._modules['MusicPlayer'] = MODULEMusic.MusicModule()
            self._modules['MusicPlayer'].start() #Start the music player, no music is loaded yet though
            self.CreateClient()
            return

        self._modules['LoadRep'] = MODULELoadReporter.LoadReporterModule() #Appends to all non-client nodes

        if self._nodeType == "Control":
            self._modules['NodeSpawn'] = MODULESpawner.SpawnerModule()
            self._modules['LoadBal'] = MODULELoadBalancer.LoadBalancerModule() #handles balancing of nodes
            self._modules['NodeSpawn'].AppendSpawnables({"Control","Echo","Dictionary","Distributor"}) #Allow spawning of these nodes
            self.CreateServer(self._IP,True)
            self._modules['NodeSpawn'].DefineSelf(self._IP, self._connectedPort)  # Set self into spawner
        elif self._nodeType == "Echo":
            self._modules['Echo'] = MODULEEcho.EchoModule()
            self.CreateServer(self._IP,False)
        elif self._nodeType == "Dictionary":
            self._modules['Dict'] = MODULEDict.DictModule()
            self.CreateServer(self._IP,False)
        elif self._nodeType == "Distributor": #used to handle the sending of files across a network
            self._modules['Distributor'] = MODULEFileSend.DistributorModule()
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
        if requestedCommand in self._nodeHandlers:
            if "LoadBal" in self._modules: #get the first node that isnt busy if the node is designed to handle load balancing
                threadList = []

                for x in self._nodeHandlers[requestedCommand]:
                    threadList.append(x.RetValues()["Thread"]) #get all threads that handle this command

                return self._modules['LoadBal'].GetFreeThread(threadList)
            else:
                #Occurs for a client who already has an active connection to this node
                return self._nodeHandlers[requestedCommand][0].RetValues()["Thread"]
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
        return {"Type" : self._nodeType, "IP" : self._IP, "Port" : self._port, "Thread" : self._threadNum}

    def AddCommand(self,commandName):
        self._commands.append(commandName)

class ClientInputReader(Thread): #Only used by a client
    #TODO make checks to ensure the client actually has an active connection before attempting any output
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
            if "@" in submittedRequest or "#" in submittedRequest or "*" in submittedRequest:
                print("One or more disallowed characters were detected. Please do not use characters '@','#' or '*' and resubmit your query")
            else:
                self._requests.append(submittedRequest)
                self._requestFlag = True


def GetConnections():
    #On file is a list of valid IPs. This contains all the IPs the server deems "available" for connection
    #On these IPs a node should be running at the port 50001 - the prime
    #A control node can spawn up new nodes on each IP

    #the client will always try to connect to the first in list on port 50001
    #the server will spawn up a node on 127.0.0.1 regardless of what is on the list
    #the file solely points to which IPs a listener might exist on - if a listener exists on 50001 and is contacted it will spawn up a new node of the requested type
    #This node will then find a port (starting at 51322) and then contact its creator and register itself. The listener should still run on 50001 to expect connections

    f = open("_ConnectionList.txt", "r")
    ValidIPs = f.readlines()[0] #gets the connection list which is split by | characters
    return ValidIPs.split("|")

def GetMyValidIP(): #Gets the IP the system can run from
    try:
        runningSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        runningSock.connect(("8.8.8.8", 80)) #Allegedly this doesnt actually need to make a connection to work, but its better to be safe and use the working 8.8.8.8 gmail IP
        return runningSock.getsockname()[0]  # return the IP address that connected (This gets the connection that an IP can access)
    except:
        print("Connection could not be made to the internet. This system requires an active internet connection to function")
        input("Press any character to continue...")
        exit()
        return 0


parentIP = 0
parentPort = 0
myIP = ""

if len(sys.argv) > 1:
    nodeRequest = sys.argv[1] #argument 1 defines the node type
    parentIP = sys.argv[2]
    parentPort = int(sys.argv[3])
else:
    nodeRequest = input("Create node: ")



NodeGen(nodeRequest, parentIP, parentPort, GetConnections(), GetMyValidIP()) #spawns up new node of specified type
