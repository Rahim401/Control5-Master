
from time import sleep
from Bridge import MasterBridge

brg = MasterBridge()
# print(brg.searchForWorker())
brg.connectToWorker("192.168.43.1")
sleep(5)
brg.disconnectFromWorker()
sleep(2)

brg.connectToWorker("192.168.43.1")
sleep(5)
brg.disconnectFromWorker()

# while brg.isConnected():
#     try:
#         task = int(input("Enter task to Perform: "))
#         if task==10:
#             break
#         brg.sendData(task,127)
#     except ValueError: pass
#     except OverflowError: pass
#
# brg.disconnectFromWorker()