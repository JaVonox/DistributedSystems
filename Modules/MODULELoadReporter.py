class LoadReporterModule: #This exists on all nodes and keeps track of how many connected clients they have
    def __init__(self):
        self._validCommands = {'*GETLOAD' : self.ReturnLoad}
        self._nodeLoad=0 #Number of connected clients

    def ReturnLoad(self, arguments): #Gets the load of this node and reports it to the asker
        return str(self._nodeLoad)

    def UpdateLoad(self,newLoad): #sets a new load, active when any client connection is made or any client connection is closed.
        oldLoad = self._nodeLoad #stores the old load of the node
        self._nodeLoad = newLoad
        if oldLoad != self._nodeLoad: #On the event of a nodes load changing
            return 1
        else:
            return 0


    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments,thread):
        return self._validCommands[command](arguments)