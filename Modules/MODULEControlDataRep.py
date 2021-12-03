import os

class ControlDataModule: #This module is used to store the necessary data for sharing between control nodes
    #This includes the playlist and valid logins
    def __init__(self):
        self._validCommands = {'*GETMUSIC' : self.GetList, '*COLLATEMUSIC' : self.CollateMusic, 'PLAYLIST' : self.ReturnNetPlaylist}
        self._nodesWithFile = {} #Thread : {Music List}

    def AppendOwnMusic(self):
        listFiles = os.listdir("Music/") #gets a list of all files in the music directory.
        for x in listFiles:
            listFiles[listFiles.index(x)] = os.path.splitext(x)[0] #gets just files without extension

        self._nodesWithFile["SELF"] = listFiles #adds own music to set

    def GetList(self,arguments,thread):
        #Returns all of the files on this device, used for coordinating all the files on the system
        return "*COLLATEMUSIC|" + "|".join(self._nodesWithFile["SELF"]) #returns the list of files without extensions

    def CollateMusic(self,arguments,thread):
        #Arguments will include all the music, thread is the selector name attached to the control node
        self._nodesWithFile[thread] = arguments[0:]
        return "#"

    def ReturnNetPlaylist(self,arguments,thread): #returns the playlist for the client
        #TODO this must check for authentication
        musicSet = []

        for x in self._nodesWithFile.values():
            for y in x:
                if not y in musicSet:
                    musicSet.append(y)

        return str(",".join(musicSet))

    def ReturnOwnMusic(self): #returns set of all music this node can handle
        return self._nodesWithFile["SELF"]

    def GetExtMusicHandler(self,target): #Return the thread of the control node able to handle this request
        for thread,objects in self._nodesWithFile.items():
            if target in objects:
                return str(thread)

        print("MUSIC HANDLER ERROR")
        return "-1"

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments,thread):
        return self._validCommands[command](arguments,thread)