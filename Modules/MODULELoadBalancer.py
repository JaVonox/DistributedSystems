class LoadBalancerModule: #This exists on only control nodes and handles the redirection of nodes and polling of connected nodes
    def __init__(self):
        self._validCommands = {"*LOADUPDATE" : self.UpdateClientLoad}
        self._maxLoad = 2 #Constant that determines how many clients can be connected before a new node is needed (0 is not a value in this)
        self._nodeLoad = {} #Thread : load

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

    def RegisterLoad(self,thread,load):
        if load != "NA": #stops registering of clients
            self._nodeLoad[thread] = load

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments,thread):
        return self._validCommands[command](arguments,thread)