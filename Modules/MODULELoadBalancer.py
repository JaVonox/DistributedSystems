class LoadBalancerModule: #This exists on only control nodes and handles the redirection of nodes and polling of connected nodes
    def __init__(self):
        self._validCommands = {"*LOADUPDATE" : self.UpdateClientLoad}
        self._maxLoad = 2 #Constant that determines how many clients can be connected before a new node is needed (0 is not a value in this)
        self._myIPLoad = 3 #The constant that controls how many systems can exist on a given IP before a new connection must be declared
        self._nodeLoad = {} #Thread : load
        self._maxIPFlag = False #True if the max number of nodes on one IP is reached

    def UpdateClientLoad(self, arguments,thread):
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

    def UpdateSelfLoadFlag(self,spawnedNodes): #checks how many non-client nodes have been spawned, and spawns up a new control node if needed
        if self._myIPLoad < spawnedNodes:
            self._maxIPFlag = True
        else:
            self._maxIPFlag = False

    def GetNewNodeNeeded(self): #checks if a node must be spawned on another IP
        if self._maxIPFlag == True:
            return True
        else:
            return False

    def RegisterLoad(self,thread,load):
        if load != "NA": #stops registering of clients
            self._nodeLoad[thread] = load

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments,thread):
        return self._validCommands[command](arguments,thread)