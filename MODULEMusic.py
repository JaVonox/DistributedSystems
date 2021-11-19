from audioplayer import AudioPlayer

class MusicModule: #Client only Module
    def __init__(self):
        self._validCommands = {"VOLUME" : self.PlayMusic}

    def PlayMusic(self, arguments):
        AudioPlayer("Music/Beepy/Moonsetter.mp3").play(block=True)

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments):
        return self._validCommands[command](arguments)