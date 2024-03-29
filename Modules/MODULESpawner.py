import subprocess
from Modules import MODULEEcho
from Modules import MODULEDict
from Modules import MODULEAuth
from Modules import MODULEFileSend

class SpawnerModule:
    def __init__(self):
        self._validCommands = {}
        self._myIP = ""
        self._myPort = ""
        self._validNodes = {}
        self._canRecieveRedir = True #set by the load balancer - determines if this node is able to spawn new nodes

    def Spawn(self,NodeType):
        subprocess.Popen(['python', 'Node.py', NodeType,str(self._myIP),str(self._myPort)],creationflags=subprocess.CREATE_NEW_CONSOLE)  # subprocessing based node generation. Adds argument control to define node type to generate
        return "New " + NodeType + " Node Generated"

    def DefineSelf(self,myIP,myPort):
        self._myIP = myIP
        self._myPort = myPort

    def UpdateRedir(self,value): #sets the redirect mode - this is set by the loadbalancer and determines if the node can accept new nodes
        self._canRecieveRedir = value

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments,thread):
        return self._validCommands[command](arguments,thread)

    #Adds all spawnable nodes to the valid nodes function
    def AppendSpawnables(self, nodesList): #nodesList contains all the names of nodes that this node may spawn
        self._validNodes.clear()

        for node in spawnables.keys() and nodesList: #check if in both nodes list and spawnables
            self._validNodes[node] = spawnables[node].ReturnCommands()
        pass

    def AppendMusicSpawnables(self,ownMusic): #Adds the music that a spawnable distributor will be able to handle on spawn
        if "Distributor" in self._validNodes:
            for x in ownMusic:
                self._validNodes["Distributor"].append("!PLAY:" + x)


    def GetSpawnableCommands(self): #return dictionary of all valid commands
        commandsAvailable = []

        #adds all existing commands to an array
        for x in self._validNodes.values():
            for y in x: #iterate through this lists commands
                commandsAvailable.append(y)


        return commandsAvailable

    def GetCommandHandler(self, command): #get which spawnable can create this command
        if command not in self.GetSpawnableCommands():
            return "#"
        else:
            for x in self._validNodes.keys(): #go through each key in validNodes
                if command in self._validNodes[x]: #check if the requested command is contained
                    return x
            return "#"

spawnables = {  # list of all possible nodes to spawn
    "Control" : SpawnerModule(),
    "Echo": MODULEEcho.EchoModule(),
    "Dictionary": MODULEDict.DictModule(),
    "Distributor": MODULEFileSend.DistributorModule(),
    "Authentication" : MODULEAuth.AuthenticationModule()}