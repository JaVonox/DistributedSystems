import socket
import selectors

class HeartbeatModule:
    def __init__(self):
        self._validCommands = {}
        # Network components
        self._myOwnerIP = 0
        self._myOwnerPort = 0

    def DefineSelf(self,myOwnerIP,myOwnerPort):
        self._myOwnerIP = myOwnerIP #defines the module owner
        self._myOwnerPort = myOwnerPort

    def HeartbeatPort(self, IP, Port):
        heartbeatSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        heartbeatResult = heartbeatSock.connect_ex((IP, Port))  # attempt connection to port. returns 0 if exists

        heartbeatSock.close()

        if heartbeatResult == 0:  # if the server on this port exists
            print(f"Server({self._myOwnerIP},{self._myOwnerPort})HB: heartbeat to ({IP},{Port}) succeeded") #TODO fix to be either server or client
            return True
        else:
            print(f"Server({self._myOwnerIP},{self._myOwnerPort})HB: heartbeat to ({IP},{Port}) failed")
            return False


    def FindNextPort(self,IP,startingPort): #iterate through ports on ip to find next available port
        desiredPort = startingPort  # next available port

        while True:
            if self.HeartbeatPort(IP, desiredPort):
                desiredPort = desiredPort + 1
            else:
                break

        return desiredPort

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments):
        return self._validCommands[command](arguments)