from time import sleep,time
from utils import recvFull,sendString,recvString
from Bridge import MasterBridge,TaskManager


class Control(TaskManager):
    def __init__(self,ipAddr):
        self.__brg = MasterBridge()
        self.__ipAddr = ipAddr

    def isConnected(self):
        return self.__brg.isConnected()

    def connect(self):
        if not self.isConnected():
            self.__brg.connectToWorker(self.__ipAddr,self)

    def disConnect(self):
        if self.isConnected():
            self.__brg.disconnectFromWorker()

    def handleReplay(self, replayId, data):
        print(f"\rGot Replay({replayId}):",data,end="\nEnter Data: ")

    def handleExReplay(self,sk):
        startTime = time()
        replayId = int.from_bytes(recvFull(sk, 2), 'big', signed=True)
        print(f"\rGot ExReplay({replayId}): {recvString(sk)} and took {time() - startTime}sec", end="\nEnter Data: ")

    def echoInt(self,data):
        self.__brg.sendTask(512, int(data))

    def echoString(self,data):
        self.__brg.sendExTask(513,lambda stream: sendString(stream, data))

if __name__ == "__main__":
    ctrl = Control("192.168.43.1")
    ctrl.connect()

    while ctrl.isConnected():
        data = input("Enter Data: ")
        if data=="exit": break
        ctrl.echoString(data)
    ctrl.disConnect()
