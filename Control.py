from time import sleep,time
from utils import recvFull,sendString,recvString
from Bridge import MasterBridge,TaskManager


class Control(TaskManager):
    def __init__(self,ipAddr):
        self.__brg = MasterBridge()
        self.__ipAddr = ipAddr
        self.__replayMap = dict()
        self.__replayStatus = dict()


    def isConnected(self):
        return self.__brg.isConnected()

    def connect(self):
        if not self.isConnected():
            self.__brg.connectToWorker(self.__ipAddr,self)

    def disConnect(self):
        if self.isConnected():
            self.__brg.disconnectFromWorker()

    def handleReplay(self, replayId, data):
        print(f"\rGot Replay({replayId}):",data)

    def handleExReplay(self,sk):
        replayId = int.from_bytes(recvFull(sk, 2), 'big', signed=True)
        print(f"\rGot ExReplay({replayId}): {recvString(sk)}")

    def getSystemInfo(self, infoCode):
        self.__brg.sendTaskB(256, int.to_bytes(infoCode,1,byteorder='big',signed=False))

    def getSystemInfo2(self, infoCode):
        self.__brg.sendTaskB(257, int.to_bytes(infoCode,1,byteorder='big',signed=False))
    # def echoInt(self,data):
    #     self.__brg.sendTask(512, int(data))
    #
    # def echoString(self,data):
    #     self.__brg.sendExTask(513,lambda stream: sendString(stream, data))

if __name__ == "__main__":
    ctrl = Control("192.168.43.1")
    ctrl.connect()
    for i in range(30):
        ctrl.getSystemInfo(i)
    sleep(3)
    ctrl.disConnect()
