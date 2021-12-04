import os

class DistributorModule:
    def __init__(self):
        self._validCommands = { "*ROUTEMUSIC" : self.RoutePlay}
        #Validcommands is initially almost empty, but it will populate itself with the music it can find on the device
        #Control nodes also have a copy of this data, and will share it with other control nodes in order to route connections
    def RequestMusic(self, title): #arguments is the file name + .wav
        try:
            reader = open("Music/" + title + ".wav", "rb")
            bytesRead = reader.read()
            reader.close()
            return "@FIL|" + str(bytesRead.hex()) #set bytes to hex for easy communication
        except FileNotFoundError:
            return "File not found"
        except:
            return "An unknown error occurred"

    def AppendMusicCommands(self):
        listFiles = os.listdir("Music/") #gets a list of all files in the music directory.
        for x in listFiles:
            listFiles[listFiles.index(x)] = os.path.splitext(x)[0] #gets just files without extension

        for x in listFiles:
            self._validCommands['!PLAY:' + str(x)] = self.PlayCommand

    def PlayCommand(self,arguments):
        musicTitle = ""

        for x in arguments:
            if ":" in str(x):
                musicTitle = x.replace(':','')

        return self.RequestMusic(musicTitle)

    def RoutePlay(self,arguments):
        return self.RequestMusic(arguments[0])

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments,thread):
        return self._validCommands[command](arguments)