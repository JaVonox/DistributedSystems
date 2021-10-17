class EchoModule:
    def __init__(self):
        # Network components
        self._echoedRequests = []

    def RequestEcho(self, input): #Simple one to one echo
        self._echoedRequests.append(input)
        return input

    def DumpEcho(self):
        return str(self._echoedRequests)