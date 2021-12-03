import os

class DistributorModule:
    def __init__(self):
        self._validCommands = {'PLAY' : self.RequestMusic}
                               #"PLAYLIST" : self.GetList}

    def RequestMusic(self, arguments): #arguments is the file name - mp3
        try:
            reader = open("Music/"+ arguments[0] + ".wav", "rb")
            bytesRead = reader.read()
            reader.close()
            return "@FIL|" + str(bytesRead.hex()) #set bytes to hex for easy communication
        except FileNotFoundError:
            return "File not found"
        except:
            return "An unknown error occurred"

    #TODO GetList must coordinate with all other nodes on the server
    #TODO may also have to check against servers that dont have an active file distribution node??

    def GetList(self,arguments):
        #if using folders, os.listdir will return folder names
        listFiles = os.listdir("Music/") #gets a list of all files in the music directory.
        for x in listFiles:
            listFiles[listFiles.index(x)] = os.path.splitext(x)[0] #gets just files without extension

        return "|".join(listFiles) #returns the list of files without extensions

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments,thread):
        return self._validCommands[command](arguments)