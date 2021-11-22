class DictModule:
    def __init__(self):
        self._validCommands = {'DICT' : self.Define ,'DICTADD' : self.AddToDict}
        self._dict = {"Hello" : "World", "Isak" : "Cool"}

    def AddToDict(self,arguments): #COMMAND DICTADD|Key|Message
        if len(arguments) >= 2:
            self._dict[arguments[0]] = arguments[1]
            return "Added value to dictionary"
        else:
            return "Invalid Arguments"

    def Define(self, arguments): #COMMAND DICT|Key
        if arguments[0] in self._dict.keys():
            return self._dict[arguments[0]]
        else:
            return "This object was not found in the dictionary"

    def ReturnCommands(self):
        return list(self._validCommands.keys())

    def CommandPoll(self,command,arguments):
        return self._validCommands[command](arguments)