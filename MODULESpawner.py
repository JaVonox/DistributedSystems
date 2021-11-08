import subprocess

class SpawnerModule:
    def __init__(self):
        self._validCommands = {'CREATE' : self.NodeSpawnParse }
        self._echoedRequests = []
        self._spawnedNodes = []
        self._parentIP = ""
        self._parentPort = ""

    def NodeSpawnParse(self,arguments): #choose which node to spawn
        if arguments[0] == "Control":
            return self.SpawnControl()
        elif arguments[0] == "Echo":
            return self.SpawnEcho()
        else:
            return "Invalid Node Type"

    def SpawnControl(self):
        subprocess.Popen(['python', 'Node.py', 'Control',str(self._parentIP),str(self._parentPort)],creationflags=subprocess.CREATE_NEW_CONSOLE)  # subprocessing based node generation. Adds argument control to define node type to generate
        return "New Control Node Generated"

    def SpawnEcho(self):
        subprocess.Popen(['python', 'Node.py', 'Echo',str(self._parentIP),str(self._parentPort)],creationflags=subprocess.CREATE_NEW_CONSOLE)  # subprocessing based node generation. Adds argument control to define node type to generate
        return "New Echo Node Generated"

    def DefineSelf(self,parentIP,parentPort):
        self._parentIP = parentIP
        self._parentPort = parentPort

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments):
        return self._validCommands[command](arguments)