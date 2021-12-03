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
from Modules import MODULEAuth
from Modules import MODULEControlDataRep

from threading import Thread
from collections import defaultdict

class NodeGen():
    def __init__(self,typeParam,parentIP,parentPort,existingIPs,myIP):
        self._connectedPort = 0
        self._IP = myIP
        self._nodeType = typeParam

        self.encodeFormat = "utf-8"
        self._modules = {}

        #Parent stores the ip of the creator for server services, and the ip of the
        self._parentIP = parentIP
        self._parentPort = parentPort

        self._knownNodes = {} # Socket Address : NodeData

        self._commandHandlers = {} #command : handler (Self commands)
        self._nodeHandlers = defaultdict(list) #command : [List of known nodes who can handle that command (in EXTNODE format)]
        self._heldCommands = [] #holds commands that require a redirect

        self._controlHB = None #Only used by control nodes - permits them to use a thread for heartbeat operations
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
            if attemptBase is True: #This occurs when the control node already exists but there is already one for this IP
                print("A control node already exists on this address.")
                input("Press any key to continue...")
                exit()
            else:
                self._connectedPort = self._modules['Heartbeat'].FindNextPort(IP, (self._parentPort + 1 if self._parentPort != 0 else 50002)) #Iterates and returns next available port on specified IP
                self._modules['Service'] = ThreadHandler.ThreadHandler(self._nodeType, self._IP, self._connectedPort)

        elif attemptBase is True: #If the node to be spawned is prime and there is no existing node on 50001
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

                self._modules['Service'].ContactNode(IP,50001,"NA",["NA"],"@REG")

                print(f"{self._nodeType}({self._IP},{self._connectedPort}): initialised on non-prime location ({self._IP}, {self._connectedPort})")
                print("Command Syntax: COMMAND|PARAMS")

                self._modules['InputReader'] = ClientInputReader() #Starts thread to handle client entering data
                self._modules['InputReader'].start()


                while True:
                    if self._modules['InputReader'].ReadFlag(): #If a client has submitted a request
                        tmpInputs = self._modules['InputReader'].ReadRequest()
                        for x in tmpInputs: #append all submitted inputs
                            if self.CheckSelfCommands(x):
                                commands = x.split("|") #Gets the first command
                                route = self.ReturnNodeHandler(commands[0]) #return the id of the handler

                                if route == "#": #if no known node can handle this command
                                    route = self.ReturnControlID()

                                if route == "#":
                                    print("There is currently no active connection and therefore the message could not be processed")
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
                if self.ReturnNodeHandler(x.split("|")[1]) != "#" and (x.split("|")[0] in self._knownNodes or x.split("|")[0][0] == "("): #check if a handler now exists for this command and the recipient is in the list of known nodes
                    #use of check for ( stops DIRNC from being stopped
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
                    if b.RetValues()["Type"] == "Control":
                        threadOfParent = str(b.RetValues()["Thread"])
                        break
                message = str(threadOfParent) + "|*LOADUPDATE|" + self._IP + "|" + str(self._connectedPort) + "|" + str(clients) #message to send to parent to update their load balancing dataset

                self._modules['Service'].writeCommands.append(message) #This does not need to go through command parser because it is already a complete command
        if "LoadBal" in self._modules: #updates the checks to see if any new nodes can be spawned on this IP
            clients=0
            controls=[]

            for a in self._knownNodes.values():
                if a.RetValues()["Type"] == "Client": #checks number of active client connections on this IP
                    clients +=1
                elif a.RetValues()["Type"] == "Control":
                    controls.append(a)


            self._modules["LoadBal"].UpdateSelfLoadFlag(clients) #update the system to check if the requested number of clients has been reached
            self._modules["NodeSpawn"].UpdateRedir = not self._modules["LoadBal"].GetNewNodeNeeded() #the spawner is set to accept new redirects if the IP is not full

            #Finds node to balance
            if len(self._modules["LoadBal"].addressesNeedingRedirect) > 1: #due to the 2D array nature of ANR the first value is always a blank value
                deleteObj = None
                for clientToHandle in self._modules['LoadBal'].addressesNeedingRedirect[1:]: #check the amount of active redirect requests and append the written command to the output for each
                    if int(clientToHandle["ITER"]) > len(self._IPList):
                        deleteObj = self._modules['LoadBal'].addressesNeedingRedirect.index(clientToHandle)
                        #This will append the object to the deleteObj, permitting it to be contacted by the existing control
                        break

                    if clientToHandle["AWAIT"] == False: #if AWAIT is false, there is no response currently expected.
                        for x in controls:
                            if self._IPList[clientToHandle["ITER"]] == x.RetValues()["IP"]: #if the current control to check is this object
                                message = str(x.RetValues()["Thread"]) + "|"
                                message += str(self._modules['LoadBal'].SendRedirection(clientToHandle))
                                clientToHandle["AWAIT"] = True
                                self._modules['Service'].writeCommands.append(message)  #Sends a message to the control node with a client redirect request, waits for response back.
                                break

                        clientToHandle["ITER"] += 1 #If no returns came through

                if deleteObj is not None:
                    print("Couldnt find route for client. Accepting request.")
                    obj = self._modules['LoadBal'].addressesNeedingRedirect[deleteObj]
                    #The service registers itself, bypassing the client limit, as it could not find a suitable peer, and therefore must accept the connection itself
                    self._modules['Service'].ContactNode(obj["IP"], int(obj["PORT"]),{""},self._commandHandlers.keys(),"@REG") #Creates a new REG call
                    del self._modules['LoadBal'].addressesNeedingRedirect[deleteObj]
                    deleteObj = None

            #Handles any balancing that the control has commited to contacting
            if len(self._modules["LoadBal"].clientsToAccept) > 1:
                for x in self._modules["LoadBal"].clientsToAccept[1:]:
                    self._modules['Service'].ContactNode(x["IP"], int(x["PORT"]),{""},self._commandHandlers.keys(),"@REG") #Creates a new REG call

                self._modules["LoadBal"].clientsToAccept = [{}]

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

        if command[1][0] == "@":
            # Builtin Commands (start with @). Queries containing @ cannot be manually entered

            #this ensures the client reports its load as NA but other nodes report the correct load
            selfload = "NA"
            if "LoadRep" in self._modules:
                selfload = str(self._modules['LoadRep'].ReturnLoad({""}))

            if command[1] == "@REG": #GET REGISTER COMMAND - EXPECT REP RESPONSE

                if "LoadBal" in self._modules and str(command[2]) == "Client":
                    if self._modules["LoadBal"].GetNewNodeNeeded(): #If this client needs a new control node redirect
                        self._modules["LoadBal"].addressesNeedingRedirect.append({"NAME" : self._modules["LoadBal"].addressNextName, "IP" : command[3], "PORT" : command[4],"ITER" : 0, "AWAIT" : False}) #adds the element to the list of items needing redirect
                        self._modules["LoadBal"].addressNextName+=1

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

                if str(command[2]) == "Control" and self._nodeType == "Client":
                    print("Connected to control node at (" + str(command[3]) + "," + str(command[4]) + ")")

                return message

            elif command[1] == "@REP": #RESPOND TO REGISTER COMMAND - EXPECT NO RESPONSE
                newNode = ExtNode(command[2], command[3], command[4], command[0])
                self._modules['Service'].DefineType(command[0], command[2])
                self._knownNodes[command[0]] = newNode

                if "LoadBal" in self._modules: #if this module can load balance, add the node data into the load balancer
                    self._modules["LoadBal"].RegisterLoad(command[0],command[5]) #append node load

                self.DictCommand(newNode,command[6:]) #add the commands the new node can do to a list of commands tha can be processed
                return command[0] + "|#"

            elif command[1] == "@DIR": #This command is sent to a node and tells them to create a new connection with the specified IP/PORT and then use the requested command
                newID = self._modules['Service'].ContactNode(command[2], int(command[3]),selfload,self._commandHandlers.keys(),"@REG") #Creates a new REG call
                return self.CommandParser(str(newID) + "|" + command[4] + "|" + str("|".join(command[5:]))) #Calls a recursive command to alleviate issues of writing to the stream too fast

            elif command[1] == "@DIRNC":
                #Uses the direct command but without registering the connection
                #This is a very controlled command which can break the system if used incorrectly. When implementing more usages of this use caution
                self.CommandParser("(" + str(command[2]) + "," + str(command[3]) + ")|" + command[4] + "|" + str("|".join(command[5:]))) #Calls a recursive command to alleviate issues of writing to the stream too fast
                return "-1|#"
            elif command[1] == "@CLOSED": #If a network connection is closed remove its relevant data from the requested commands
                #Closed should always be received if a connection closes, since the reading node itself will create this request if it loses a connection
                if command[0] in self._knownNodes: #if the id is in the known nodes
                    deadNode = self._knownNodes[command[0]]
                    deadNodeIP = deadNode.RetValues()["IP"]
                    deadNodeType = deadNode.RetValues()["Type"]

                    self.KillNode(deadNode)
                    del self._knownNodes[command[0]] #remove node from list of nodes

                    if "LoadBal" in self._modules:
                        self._modules["LoadBal"].KillThread(command[0])
                        if deadNodeType == "Control": #Removes this control from the list of actively pinged controls - thereby allowing this control to be checked again for updates
                            self._modules["LoadBal"].KilLPingFromIP(deadNodeIP)


                return "-1|#"

            elif command[1] == "@NOSPACE": #This tells a client that there is no space on this control and to expect a redirect
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

            #Stores the key given by an auth node
            elif command[1] == "@AUTHGRANT" and self._nodeType == "Client":
                print("--- Login Accepted ---")
                self._modules['InputReader'].AuthKeyUpdate(command[2]) #Adds the auth key to the auth key processor
                return command[0] + "|#"

            elif command[1] == "@AUTHDENY" and self._nodeType == "Client":
                print("--- Invalid credentials ---")
                return command[0] + "|#"

        elif self._nodeType == "Client": #Clients only service @ commands
            return command[0] + "|#" #NOOP command

        elif self._nodeType == "Control" and str(command[1]).startswith("!PLAY"):
            #A client will only send this request to a control node if they attempt to play music that they do not have an active connection towards a handler for this song

            authResult = "ACCEPT"
            authResult = self.CheckAuthKey(command[-1],command[0])

            if authResult != "ACCEPT":
                return authResult

            musicName = ""

            if ":" in str(command[1]): #Gives musicPlayer nodes the music name as an argument
                musicName = (str(command[1].split(":")[1])) #Gets first segment after : split

            if musicName in self._modules['ControlData'].ReturnOwnMusic():
                return str(self.HandleCommandDirecting(command[0:]))  # Routes to the appropriate command
            else:
                if musicName in (self._modules['ControlData'].ReturnNetPlaylist({}, {}).split(",")):
                    #TODO add load balancing somehow
                    senderNode = self._knownNodes[command[0]]
                    controlThread = self._modules['ControlData'].GetExtMusicHandler(musicName)
                    newCommand = "*ROUTEMUSIC|" + musicName
                    return controlThread + "|@DIRNC|" + str(senderNode.RetValues()["IP"]) + "|" + str(senderNode.RetValues()["Port"]) + "|" + newCommand
                else:
                    return command[0] + "|This song is currently not available on any active member of the system"

        elif command[1] in self._commandHandlers.keys():

            #Poll authentication. If this module is the authenticator then bypass this
            if "Auth" not in self._modules:
                authResult = self.CheckAuthKey(command[-1], command[0])
                if authResult != "ACCEPT":
                    return authResult

            #Modular Commands
            #directs the command to the handling module on this node
            args = command[2:]

            if ":" in str(command[1]): #Gives musicPlayer nodes the music name as an argument
                args.append(":" + str(command[1].split(":")[1])) #Gets first segment after : split

            return command[0] + "|" + self._commandHandlers[command[1]].CommandPoll(command[1],args,command[0])

        else:

            #Authenticate for non-Auth requests

            authResult = "ACCEPT"

            if 'NodeSpawn' in self._modules:
                if self._modules['NodeSpawn'].GetCommandHandler(command[1]) != "Authentication":
                    authResult = self.CheckAuthKey(command[-1],command[0])
            else:
                authResult = self.CheckAuthKey(command[-1], command[0])

            if authResult != "ACCEPT":
                return authResult

            return str(self.HandleCommandDirecting(command[0:])) #Routes to the appropriate command

    def CheckAuthKey(self,key,target):
        if str(key) == "NOAUTH":  #TODO rework this.
            #TODO the current implementation does not account for node type, as only clients would have a request with NOAUTH at the end
            #TODO switching this to use anything aside from == "NOAUTH" will require reworking the function

            return target + "|Please login to the system"
        else:
            return "ACCEPT"

    def HandleCommandDirecting(self,command):
        # search for thread of node that can use this command
        foundNode = self.ReturnNodeHandler(command[1])

        # get node of sender - to pass to the handler node
        senderNode = None

        if command[0] in self._knownNodes:
            senderNode = self._knownNodes[command[0]]
        else:
            if str(command[0])[0] == "(": #This occurs on a DIRNC command, inwhich a connection is issued without the redirector making a connection to the client
                splitRedir = command[0].split(",")

                fixedIP = splitRedir[0].replace('(','')
                fixedPort = splitRedir[1].replace(')','')

                senderNode = ExtNode("REDIR",fixedIP,fixedPort,"NULL")
            else:
                # Forces the system to wait until the sender has been registered - This prevents issues where DIR would attempt to fire before client response
                self._heldCommands.append("|".join(command))

        if foundNode == "#" and 'NodeSpawn' in self._modules.keys():  # If the module has a nodespawner and the module does not already exist
            nodeSpawn = self._modules['NodeSpawn'].GetCommandHandler(command[1])
            if nodeSpawn != "#":
                self._modules['NodeSpawn'].Spawn(nodeSpawn)
                if not "|".join(command) in self._heldCommands:  # Prevents a bug where the request would be appended twice
                    self._heldCommands.append("|".join(command))  # adds the current command to the list of commands that need handling.
                if senderNode.RetValues()["Type"] != "REDIR":
                    return command[0] + "|Spawned handler for this command. Please wait for a response."
                else:
                    return "-1|#"
            else:
                if senderNode.RetValues()["Type"] != "REDIR":
                    return command[0] + "|This node does not know the requested command nor any nodes than can handle it"
                else:
                    return "-1|#"
        if foundNode == "#":  # No known node
            if senderNode.RetValues()["Type"] != "REDIR":
                return command[0] + "|This node does not know the requested command and lacks the ability to create new nodes" #This should never occur
            else:
                return "-1|#"
        else:
            # Thread that runs the handler + listening ports of requester + initial request of user
            # This is run when a user first requests a command that a different node may handle, after this the connections will be client to this node directly
            return foundNode + "|@DIR|" + str(senderNode.RetValues()["IP"]) + "|" + str(senderNode.RetValues()["Port"]) + "|" + str("|".join(command[1:]))

    def EstablishControlNetwork(self): #This sends a contact request to all listed controls in the IP list - skipping those that an active connection already exists for.
        #This is only used by control nodes

        controls = []  # excludes self

        for a in self._knownNodes.values():
            if a.RetValues()["Type"] == "Control":
                controls.append(a)

        if len(controls) + 1 < len(self._IPList):  # Checks if there is missing controls contacted
            while True:
                KnownControls = []

                for a in self._knownNodes.values(): #iterate through all known nodes
                    if a.RetValues()["Type"] == "Control":
                        KnownControls.append(a.RetValues()["IP"]) #adds the IPs to the list of known IPs with active connections

                for x in self._IPList:
                    if x in KnownControls or x == self._IP or x in self._modules['LoadBal'].pingedControlIPs: #check if this IP is in the set of known IPs
                        pass
                    else:
                        #Create a REG connection to all uncontacted control nodes
                        #Heartbeating a location takes a lot of time, which is why this segment must be on a thread
                        if self._modules['Heartbeat'].HeartbeatPort(x,50001): #Check if a control exists on the specified location
                            #adds to known controls to stop repeat calls + adds to list of heartbeats that went through - effectively saying "this is where a control node must exist"
                            #a control will be removed from this set if it disconnects
                            self._modules['LoadBal'].pingedControlIPs.append(str(x))

                            #Send REP to uncontacted control node - this means no response is expected, but this control node should register itself.
                            #Since all control nodes should do this, all should register eachother if this function is run on random intervals

                            newThread = self._modules['Service'].ContactNode(x, 50001,"NA",{"CTRL"},"@REP") #Creates a new REG call to the uncontacted control node
                            self._modules['Service'].ContactNode(x, 50001,"NA","*GETMUSIC","NULL") #Call to get music from node
                            #TODO need to remove music listing from playlist if the node goes down

                time.sleep(2.5) #Pause for a period of time to free up usage space

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
            self._modules['ControlData'] = MODULEControlDataRep.ControlDataModule() #Used for coordinating network data
            self._modules['ControlData'].AppendOwnMusic()
            self._modules['NodeSpawn'].AppendSpawnables({"Control","Echo","Dictionary","Distributor","Authentication"}) #Allow spawning of these nodes
            self._modules['NodeSpawn'].AppendMusicSpawnables(self._modules['ControlData'].ReturnOwnMusic())
            self.CreateServer(self._IP,True)
            self._modules['NodeSpawn'].DefineSelf(self._IP, self._connectedPort)  # Set self into spawner

            self._controlHB = Thread(target=self.EstablishControlNetwork, args=[]) #starts control specific thread which searches for all other control nodes
            self._controlHB.start()

        elif self._nodeType == "Echo":
            self._modules['Echo'] = MODULEEcho.EchoModule()
            self.CreateServer(self._IP,False)
        elif self._nodeType == "Dictionary":
            self._modules['Dict'] = MODULEDict.DictModule()
            self.CreateServer(self._IP,False)
        elif self._nodeType == "Distributor": #used to handle the sending of files across a network
            self._modules['Distributor'] = MODULEFileSend.DistributorModule()
            self._modules['Distributor'].AppendMusicCommands() #add all ! commands to the distributor node
            self.CreateServer(self._IP,False)
        elif self._nodeType == "Authentication":
            self._modules['Auth'] = MODULEAuth.AuthenticationModule()
            self.CreateServer(self._IP,False)
            self._modules['Auth'].CacheLogins()
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

    def ReturnControlID(self): #gets the ID of the control node for the client to contact. there should only ever be one control node in the known nodes for a client
        for x in self._knownNodes.values():
            if x.RetValues()["Type"] == "Control":
                return x.RetValues()["Thread"]

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
    def __init__(self):
        Thread.__init__(self)
        self._requests = []
        self._requestFlag = False #False if no new input, True if new Input
        self._myAuthKey = "NOAUTH" #Sets an auth key on login request

    def AuthKeyUpdate(self,newAuth):
        self._myAuthKey = newAuth

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
                self._requests.append(submittedRequest + "|" + self._myAuthKey) #TODO if any changes are made to security, this needs to be changed since it displays the auth key
                #TODO however, if auth keys are client specific, this wont matter
                self._requestFlag = True


def GetConnections():
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
    if nodeRequest != "Client" and nodeRequest != "Control":
        print("Valid inputs are 'Client' and 'Control'")
        input("Press any character to continue...")
        exit()


NodeGen(nodeRequest, parentIP, parentPort, GetConnections(), GetMyValidIP()) #spawns up new node of specified type
