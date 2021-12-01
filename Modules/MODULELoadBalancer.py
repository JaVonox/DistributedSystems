class LoadBalancerModule: #This exists on only control nodes and handles the redirection of nodes and polling of connected nodes
    def __init__(self):
        self._validCommands = {"*LOADUPDATE" : self.UpdateClientLoad, "*CANACCEPTLOAD" : self.CanAcceptNewNode}
        self._maxLoad = 2 #Constant that determines how many clients can be connected before a new node is needed (0 is not a value in this)
        self._nodeLoad = {} #Thread : load. Stores all known non-clients and how many clients they have connected.

        self._maxClientsFlag = False #True if the max number of clients on one control is reached
        self._desiredClients = 3 #This constant determines how many clients a node wishes to handle - this is not a hard limit, but the control will start attempting redirects to controls if this limit is reached.
        self.addressesNeedingRedirect = [] #(IP,Port,Iteration) Stores which items need redirects

    def UpdateClientLoad(self, arguments,thread): #for non-client nodes
        self._nodeLoad[thread] = arguments[2] #Update the load of the thread
        return "#" #returns no response code

    def GetFreeThread(self,threads):
        returnCommand = "#" #if no available node, tell the load balancing node to create a new node of this type

        for x in threads:
            if x in self._nodeLoad.keys():
                if int(self._nodeLoad[x]) < self._maxLoad: #check if the node is below its limit. The load of a node only updates after a connection therefore there must be one free slot
                    returnCommand = x
                    break

        #TODO spawn new node if the node is at its limit
        return returnCommand

    def KillThread(self,thread):
        if thread in self._nodeLoad: #check this node is being balanced
            del self._nodeLoad[thread] #removes thread from load balancing

    def RegisterLoad(self,thread,load):
        if load != "NA": #stops registering of clients
            self._nodeLoad[thread] = load

    #Balancing between controls

    def UpdateSelfLoadFlag(self,numberOfClients): #checks how many non-client nodes have been spawned, and spawns up a new control node if needed
        if self._desiredClients <= numberOfClients:
            self._maxClientsFlag = True
        else:
            self._maxClientsFlag = False

    def GetNewNodeNeeded(self): #checks if a control must be spawned on another IP
        return self._maxClientsFlag

    def CanAcceptNewNode(self,arguments,thread):
        if self._maxClientsFlag == True: #TODO this is dumb
            return "YAOKBRO"
        else:
            return "NAHBRO"

    def SendRedirection(self,item): #This returns a redirect message for the address needing redirect in question, or removes it from the active objects if needed
        pass

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments,thread):
        return self._validCommands[command](arguments,thread)