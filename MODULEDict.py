class DictModule:
    def __init__(self):
        self._validCommands = {'DICT' : self.Define ,'DICTADD' : self.AddToDict}
        self._dict = {"Hello" : "World", "Isak" : "Cool"}

    def AddToDict(self,arguments): #COMMAND DICTADD|Key|Message
        self._dict[arguments[0]] = arguments[1]
        return "Added value to dictionary"

    def Define(self, arguments): #COMMAND DICT|Key
        return self._dict[arguments[0]]

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments):
        return self._validCommands[command](arguments)