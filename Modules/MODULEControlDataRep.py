import os
from collections import defaultdict

class ControlDataModule: #This module is used to store the necessary data for sharing between control nodes
    #This includes the playlist and valid logins
    def __init__(self):
        self._validCommands = {'*GETMUSIC' : self.GetList, '*COLLATEMUSIC' : self.CollateMusic, 'PLAYLIST' : self.ReturnNetPlaylist}
        self._nodesPerFile = {} #Thread : {Music List}

    def AppendOwnMusic(self):
        listFiles = os.listdir("Music/") #gets a list of all files in the music directory.
        for x in listFiles:
            listFiles[listFiles.index(x)] = os.path.splitext(x)[0] #gets just files without extension

        self._nodesPerFile["SELF"] = listFiles #adds own music to set

    def GetList(self,arguments,thread):
        #Returns all of the files on this device, used for coordinating all the files on the system
        return "*COLLATEMUSIC|" + "|".join(self._nodesPerFile["SELF"]) #returns the list of files without extensions

    def CollateMusic(self,arguments,thread):
        #Arguments will include all the music, thread is the selector name attached to the control node
        self._nodesPerFile[thread] = arguments[0:]
        return "#"

    def ReturnNetPlaylist(self,arguments,thread): #returns the playlist for the client
        musicSet = []

        for x in self._nodesPerFile.values():
            for y in x:
                if not y in musicSet:
                    musicSet.append(y)

        return str(",".join(musicSet))


    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments,thread):
        return self._validCommands[command](arguments,thread)