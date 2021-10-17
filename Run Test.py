import Node
import time

nodeRequest = input("Define node to start:")
nodeVar = None

if nodeRequest == "Control":
    nodeVar = Node.NodeGen("Control")
elif nodeRequest == "Client":
    nodeVar = Node.NodeGen("Client")
elif nodeRequest == "Echo":
    nodeVar = Node.NodeGen("Echo")

#module1 = Node.NodeGen("Client")

#server2 = Node.NodeGen()
#server2.CreateServer()

"""
server2 = Node.NodeGen()
server2.CreateServer()

server1 = NodeServer.NodeServer("127.0.0.1", 12346)
server2 = NodeServer.NodeServer("127.0.0.1", 12347)
server3 = NodeServer.NodeServer("127.0.0.1", 12348)

server1.start()
server2.start()
server3.start()
time.sleep(2)

module1 = NodeClient.NodeClient("module1", "127.0.0.1", 12346)
module2 = NodeClient.NodeClient("module2", "127.0.0.1", 12347)
module3 = NodeClient.NodeClient("module3", "127.0.0.1", 12348)


module1.start()
time.sleep(1)
module2.start()
time.sleep(1)
module3.start()
time.sleep(1)


module1.postMessage("Module 1 go")
time.sleep(2)
module2.postMessage("Module 2 go")
time.sleep(2)
module1.postMessage("Module 1 go 2")
time.sleep(2)
module3.postMessage("Module 3 is late")

time.sleep(5)

module1.postMessage("Module 1 go")
module2.postMessage("Module 2 go")
module1.postMessage("Module 1 go 2")
module3.postMessage("Module 3 is late")
"""