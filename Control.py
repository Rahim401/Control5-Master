from threading import Condition
from time import time
from Bridge import MasterBridge, TaskManager
from utils import ByteBuffer


class Control(TaskManager):
    def __init__(self,ipAddr):
        self.__brg = MasterBridge(self)
        self.__ipAddr = ipAddr
        self.__replayMap = dict()
        self.__replayMapLock = Condition()

    def isConnected(self):
        return self.__brg.isConnected()

    def connect(self):
        if not self.isConnected():
            self.__brg.connectToWorker(self.__ipAddr)
    def disConnect(self):
        if self.isConnected():
            self.__brg.disconnectFromWorker()

    def handleReplay(self, replayId, data):
        with self.__replayMapLock:
            if replayId in self.__replayMap:
                self.__replayMap[replayId] = data
                self.__replayMapLock.notify_all()
    def onConnected(self): print("Connected")

    def onDisconnected(self):
        with self.__replayMapLock:
            self.__replayMapLock.notify_all()
        print("Disconnected")


    def reserveTaskId(self,taskId):
        with self.__replayMapLock:
            for uid in range(16):
                nTaskId = (uid << 12) | taskId
                if nTaskId not in self.__replayMap:
                    self.__replayMap[nTaskId] = None
                    return nTaskId
    def sendTask(self, taskId, data, willReturn=False, blockAndGet=True):
        if not self.isConnected():
            return None

        replayId = taskId
        if willReturn:
            replayId = self.reserveTaskId(taskId)
        if replayId is not None:
            self.__brg.sendTask(
                int.to_bytes(
                    replayId,2,
                    byteorder='big',
                    signed=False
                ) + data
            )

        if willReturn and blockAndGet:
            return self.recvReplay(replayId)
        return replayId

    @staticmethod
    def decodeReplay(taskId, data):
        buffer = ByteBuffer(data)
        if taskId == 256:
            return buffer.getUTF(2)
    def isReplayAvailable(self, replayId):
        return self.__replayMap[replayId] is not None
    def recvReplay(self, replayId, timeout=None):
        if not self.isConnected(): return
        with self.__replayMapLock:
            if replayId not in self.__replayMap:
                raise ValueError(f"Not waiting for the replayId({replayId})")
            self.__replayMapLock.wait_for(
                lambda: self.isReplayAvailable(replayId) or not self.isConnected(),
                timeout=timeout
            )
            if not self.isReplayAvailable(replayId):
                return
            return self.decodeReplay(
                replayId & 4095,
                self.__replayMap.pop(replayId)
            )

    def getSystemInfo(self, infoCode, blockAndGet=True):
        bytBuf = ByteBuffer.makeBuffer(Byt=infoCode)
        return self.sendTask(256,bytBuf,willReturn=True,blockAndGet=blockAndGet)

if __name__ == "__main__":
    ctrl = Control("192.168.43.1")
    ctrl.connect()
    start = time()
    i = 0
    while i<=10000 and ctrl.isConnected():
        lst = []
        for _ in range(16):
            lst.append(ctrl.getSystemInfo(i%20,blockAndGet=False))
            i += 1

        for id in lst:
            print(id,ctrl.recvReplay(id))

        lst.clear()

    print("Time:",(time()-start)/10000)