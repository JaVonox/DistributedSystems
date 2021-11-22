class DistributorModule:
    def __init__(self):
        self._validCommands = {'PLAY' : self.RequestMusic}

    def RequestMusic(self, arguments): #arguments is the file name - mp3
        try:
            reader = open("Music/"+ arguments[0] + ".mp3", "rb")
            bytesRead = reader.read()
            reader.close()
            return "@FIL|" + str(bytesRead.hex()) #set bytes to hex for easy communication
        except FileNotFoundError:
            return "File not found"
        except:
            return "An unknown error occurred"

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments):
        return self._validCommands[command](arguments)