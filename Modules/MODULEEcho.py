class EchoModule:
    def __init__(self):
        self._validCommands = {'ECHO' : self.RequestEcho ,'ECHODUMP' : self.DumpEcho}
        self._echoedRequests = []

    def RequestEcho(self, arguments): #Simple one to one echo
        self._echoedRequests.append(arguments[0])
        return arguments[0]

    def DumpEcho(self,arguments):
        return str(self._echoedRequests)

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments,thread):
        return self._validCommands[command](arguments)