import subprocess

class SpawnerModule:
    def __init__(self):
        self._validCommands = {'CREATE' : self.NodeSpawnParse }
        self._echoedRequests = []
        self._spawnedNodes = []
        self._myIP = ""
        self._myPort = ""
        self._validNodes = ["Control","Echo","Dictionary"] #Constant

    def NodeSpawnParse(self,arguments): #choose which node to spawn
        if arguments[0] in self._validNodes:
            return self.Spawn(arguments[0])
        else:
            return "Invalid Node Type"

    def Spawn(self,NodeType):
        subprocess.Popen(['python', 'Node.py', NodeType,str(self._myIP),str(self._myPort)],creationflags=subprocess.CREATE_NEW_CONSOLE)  # subprocessing based node generation. Adds argument control to define node type to generate
        return "New " + NodeType + " Node Generated"

    def DefineSelf(self,myIP,myPort):
        self._myIP = myIP
        self._myPort = myPort

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments):
        return self._validCommands[command](arguments)