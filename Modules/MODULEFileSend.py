import os

class DistributorModule:
    def __init__(self):
        self._validCommands = {'SPAWN' : self.SpawnTemp}
        #TODO add !Play to ControlDataRep, client will automatically route to a command with a known music, but for invalid titles it must route to Control

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

    def SpawnTemp(self,arguments): #TODO a server must spawn up a distributor node now, probably should also append valid music. This is a temporary file
        return "SPAWNED"

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

        print(musicTitle)
        #TODO check "" can never happen
        return self.RequestMusic(musicTitle)

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments,thread):
        return self._validCommands[command](arguments)