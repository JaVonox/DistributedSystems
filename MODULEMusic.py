from audioplayer import AudioPlayer
import tempfile
import os
import time
from threading import Thread #This must be a thread so music can play while the rest of the system functions

class MusicModule(Thread): #Client only Module
    def __init__(self):
        Thread.__init__(self)
        self._currentPlayer = None
        self._validCommands = {"VOLUME" : self.SetSound,
                               "PLAY" : self.PlayMusic,
                               "RESUME" : self.ResumeSound,
                               "PAUSE" : self.PauseSound}

    def PlayMusic(self, arguments):
        tempF = tempfile.NamedTemporaryFile(dir="cache",delete=False) #this is a 'fake' file to be used for reading in data from a request

        tempF.write(arguments[0])
        filename = os.path.basename(tempF.name)

        tempF.close() #closes allowing the audioplayer to access the file
        self._currentPlayer = AudioPlayer("cache/"+filename)
        self._currentPlayer.play(block=False)  # the file is deleted inside this

    #TODO add checks that the system is actually playing

    def SetSound(self,arguments):
        self._currentPlayer.volume = arguments[0]

    def PauseSound(self):
        self._currentPlayer.pause()

    def ResumeSound(self):
        self._currentPlayer.resume()

    def run(self):
        while True:
            pass
            time.sleep(0.05) #stop the system using too much memory

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments):
        return self._validCommands[command](arguments)

