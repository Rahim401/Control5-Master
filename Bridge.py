
from random import randint
from time import time,sleep
from threading import Thread, current_thread
from socket import gethostname, gethostbyname_ex
from socket import socket, AF_INET, SOCK_DGRAM, timeout

ScanRequestTaskId = 0
ConnectRequestTaskId = 63

ConnectionTaskId = 64
BeatTaskId = 65
ExtendedTaskId = 66
DisconnectTaskId = 255

MainPort = 32654
DataPort = MainPort + 1
HostName = gethostname()
Nw2Scan = ()

class TaskManager:
    def onConnected(self): pass
    def onDisconnected(self): pass

    def handleReplay(self,replayId,data):
        pass

class MasterBridge:
    RepeatScan = 10
    InitSize = 64
    Inter = 1
    InterBy4 = Inter / 4
    LCInter = 0.1

    def __init__(self, taskManager:TaskManager):
        self.__mainDSkLane = socket(AF_INET, SOCK_DGRAM)
        self.__isAlive = False
        self.__workerAddr = None

        self.__sndRecvThread = None
        self.__nextBeatAt = -1
        self.__taskManager = taskManager

    def isConnected(self):
        return self.__isAlive
    def getExStream(self):
        if self.isConnected():
            return
        return

    @staticmethod
    def __updateScanAddr():
        MasterBridge.Nw2Scan = [
            ip[:ip.rfind('.')]+".255" for ip in gethostbyname_ex(HostName)[2]
        ] + ["127.0.0.1",]

    def searchForWorker(self):
        workerLst = set()
        scanPack = bytes((0,ScanRequestTaskId,randint(0,255),0,0,0))

        self.__updateScanAddr()
        self.__mainDSkLane.settimeout(MasterBridge.LCInter)
        for _ in range(MasterBridge.RepeatScan):
            try:
                for nwAddr in Nw2Scan:
                    self.__mainDSkLane.sendto(
                        scanPack,
                        (nwAddr, MainPort)
                    )
                data,addr = self.__mainDSkLane.recvfrom(6)
                if data[:3]==scanPack[:3]:
                    workerLst.add(addr[0])
            except timeout:
                pass
        self.__mainDSkLane.settimeout(0)
        return workerLst
    def connectToWorker(self,ipAddr):
        self.__workerAddr = (ipAddr, MainPort)
        sndPack = bytearray((0,ConnectRequestTaskId,randint(0,255),0,0,0))

        try:
            self.__mainDSkLane.sendto(sndPack, self.__workerAddr)
            self.__mainDSkLane.settimeout(MasterBridge.LCInter)
            while True:
                data,addr = self.__mainDSkLane.recvfrom(64000)
                sndPack[1] = ConnectionTaskId; sndPack[3] = 1
                if addr==self.__workerAddr and data[:4] == sndPack[:4]:
                    break

            sndPack[3] = 2
            self.__mainDSkLane.sendto(sndPack, self.__workerAddr)

            self.__isAlive = True
            self.__sndRecvThread = Thread(
                target=self.__sendRecvLooper,
                daemon=True
            )
            self.__sndRecvThread.start()
            self.__taskManager.onConnected()
        except timeout: self.disconnectWorker()
        except ConnectionError: self.disconnectWorker()


    # 0: 0.055, 0.25: 0.11, 0.5: 0.26, 0.75: 0.5
    def __sendRecvLooper(self):
        beatBuf = bytes((0,BeatTaskId,0,0,0,0))
        nextReplyWithin = -1
        self.__mainDSkLane.settimeout(MasterBridge.InterBy4)

        self.__mainDSkLane.sendto(beatBuf, self.__workerAddr)
        while self.isConnected():
            try:
                data,addr = self.__mainDSkLane.recvfrom(64000)
                if addr == self.__workerAddr:
                    nextReplyWithin = time() + MasterBridge.Inter
                    taskId = int.from_bytes(data[:2], 'big', signed=False)
                    if taskId == BeatTaskId: pass
                    elif taskId == DisconnectTaskId: break
                    else:
                        self.__taskManager.handleReplay(
                            taskId,
                            data
                        )
            except timeout:
                if time() > nextReplyWithin:
                    break
            except ConnectionError: pass
            now = time()
            if now > self.__nextBeatAt:
                self.__mainDSkLane.sendto(beatBuf, self.__workerAddr)
                self.__nextBeatAt = now + MasterBridge.InterBy4
        self.disconnectWorker()

    def sendTask(self,data):
        if not self.isConnected():
            return
        try:
            self.__mainDSkLane.sendto(data[:6]+(b"\x00"*(6-len(data))), self.__workerAddr)
            self.__nextBeatAt = time() + MasterBridge.InterBy4
        except IOError:
            pass
    def disconnectWorker(self):
        if self.__workerAddr is None:
            return

        if self.__isAlive:
            self.__isAlive = False
            if self.__sndRecvThread is not None and current_thread() != self.__sndRecvThread:
                self.__sndRecvThread.join()
            # if self.__sndRecvThread is not None and current_thread() != self.recvThread:
            #     self.recvThread.join()
            self.__workerAddr = None
            self.__taskManager.onDisconnected()

    def disconnectFromWorker(self):
        if not self.isConnected():
            return
        self.__mainDSkLane.sendto(bytes((0, DisconnectTaskId, 0, 0, 0, 0)), self.__workerAddr)
        self.disconnectWorker()