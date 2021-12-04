class AuthenticationModule:
    #auth module will:
    #have a constant code
    def __init__(self):
        self._validCommands = {'LOGIN' : self.CheckLogin}
        self._echoedRequests = []
        self._logins = {}
        self._validKey = "AUTHGRANT"

    def CheckLogin(self, arguments): #Checks if the login is in the list of valid logins
        #arguments Login|Username|Password
        if arguments[0] in self._logins.keys():
            if arguments[1] == self._logins[arguments[0]]:
                return "@AUTHGRANT|" + str(self._validKey)
        return "@AUTHDENY|"

    def CacheLogins(self):
        f = open("_Logins.txt", "r")
        dataSet = f.readlines()

        for line in dataSet:
            parsedLine = line.split("|") #0 is
            self._logins[str(parsedLine[0].strip())] = str(parsedLine[1].strip())

        #Gets all valid logins on this device. ran on startup of the system

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments,thread):
        return self._validCommands[command](arguments)