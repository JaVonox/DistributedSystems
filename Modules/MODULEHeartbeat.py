import socket
import selectors

class HeartbeatModule:
    def __init__(self,Type):
        self._validCommands = {}
        self._myOwnerType = Type
        # Network components
        self._myOwnerIP = 0
        self._myOwnerPort = 0

    def DefineSelf(self,myOwnerIP,myOwnerPort):
        self._myOwnerIP = myOwnerIP #defines the module owner
        self._myOwnerPort = myOwnerPort

    def HeartbeatPort(self, IP, Port): #TODO change name?
        heartbeatSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        heartbeatResult = heartbeatSock.connect_ex((IP, Port))  # attempt connection to port. returns 0 if exists

        heartbeatSock.close()

        if heartbeatResult == 0:  # if the server on this port exists
            return True
        else:
            return False


    def FindNextPort(self,IP,startingPort): #iterate through ports on ip to find next available port
        desiredPort = startingPort  # next available port

        #TODO this assumes clients wont join at the same time
        while True:
            if self.HeartbeatPort(IP, desiredPort):
                desiredPort = desiredPort + 1
            else:
                break

        return desiredPort

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments,thread):
        return self._validCommands[command](arguments)