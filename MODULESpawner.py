import subprocess

class SpawnerModule:
    def __init__(self):
        # Network components
        self._echoedRequests = []
        self._spawnedNodes = []

    def NodeSpawnParse(self,nodeType,parentIP,parentPort): #choose which node to spawn
        if nodeType == "Control":
            return self.SpawnControl(parentIP,parentPort)
        else:
            return 0

    def SpawnControl(self,parentIP,parentPort):
        subprocess.Popen(['python', 'Node.py', 'Control',str(parentIP),str(parentPort)],creationflags=subprocess.CREATE_NEW_CONSOLE)  # subprocessing based node generation. Adds argument control to define node type to generate
        return 1