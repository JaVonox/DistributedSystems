class DictModule:
    def __init__(self):
        # Network components
        self._dict = {"Hello" : "World", "Isak" : "Cool"}

    def AddToDict(self,key,message): #COMMAND DICTADD|Key|Message
        self._dict[key] = message

    def Define(self, key): #COMMAND DICT|Key
        return self._dict[key]
