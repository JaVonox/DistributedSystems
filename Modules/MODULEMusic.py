from audioplayer import AudioPlayer
import tempfile
import os
import time
from threading import Thread #This must be a thread so music can play while the rest of the system functions

class MusicModule(Thread): #Client only Module
    def __init__(self):
        Thread.__init__(self)
        self._volume = 20
        self._currentPlayer = None
        self._validCommands = {"VOLUME" : self.SetSound,
                               "RESUME" : self.ResumeSound,
                               "PAUSE" : self.PauseSound,
                               "STOP" : self.StopSound}

    def PlayMusic(self, arguments):
        try:
            tempF = tempfile.NamedTemporaryFile(dir="cache",delete=False) #this is a 'fake' file to be used for reading in data from a request

            tempF.write(arguments[0])
            filename = os.path.basename(tempF.name)

            tempF.close() #closes allowing the audioplayer to access the file
            self._currentPlayer = AudioPlayer("cache/"+filename)
            self._currentPlayer.volume = self._volume
            self._currentPlayer.play(block=False)  # the file is deleted inside this
            print("Music Player: Playing")
        except Exception as e:
            print("Music Player: Could not play. Did you spell the song title correctly?")

    def SetSound(self,arguments):
        if not str(arguments[0]).isdigit():
            print("Music Player: Invalid volume value")
        else:
            newVolume = max(0,min(100,int(arguments[0])))
            if self._currentPlayer is not None:
                self._currentPlayer.volume = newVolume

            self._volume = newVolume
            print("Music Player: Set volume to " + str(newVolume) + "/100")

    def PauseSound(self,arguments):
        if self._currentPlayer is not None:
            self._currentPlayer.pause()
            print("Music Player: Paused song")
        else:
            print("Music Player: Nothing is currently playing!")

    def ResumeSound(self,arguments):
        if self._currentPlayer is not None:
            self._currentPlayer.resume()
            print("Music Player: Resumed song")
        else:
            print("Music Player: Nothing is currently playing!")

    def StopSound(self,arguments):
        if self._currentPlayer is not None:
            self._currentPlayer = None
            print("Music Player: Stopped playing")
        else:
            print("Music Player: Nothing is currently playing!")

    def run(self):
        while True:
            pass
            time.sleep(0.05) #stop the system using too much memory

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments,thread):
        return self._validCommands[command](arguments)

