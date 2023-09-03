
from time import sleep,time
from utils import toBcAddress,recvFull
from random import randbytes,randint
from threading import Thread,current_thread
from socket import socket,AF_INET,SOCK_DGRAM,SOCK_STREAM,timeout,MSG_WAITALL
from socket import getaddrinfo,gethostname,getnameinfo,if_nameindex,gethostbyname_ex,gethostbyname

ScanRequestTaskId = 0
ConnectRequestTaskId = 63

ConnectionTaskId = 64
BeatTaskId = 65
ExtendedTaskId = 66
DisconnectTaskId = 255

class TaskManager:
    def handleReplay(self,replayId,data):
        pass
    def handleExReplay(self,sk:socket):
        pass

class MasterBridge:
    MainPort = 32654
    DataPort = MainPort+1
    HostName = gethostname()
    Nw2Scan = ()

    RepeatScan = 10
    InitSize = 64
    Inter = 1
    InterBy4 = Inter / 4
    LCInter = 0.1

    def __init__(self):
        self.__mainDSkLane = socket(AF_INET, SOCK_DGRAM)
        self.__isAlive = False
        self.__workerAddr = None

        self.__sndRecvThread = None
        self.__nextBeatAt = -1

        self.__eDataSSkLane = None
        self.__eDataWaitingList = {}

    def isConnected(self):
        return self.__isAlive

    @staticmethod
    def __updateScanAddr():
        MasterBridge.Nw2Scan = [
            ip[:ip.rfind('.')]+".255" for ip in gethostbyname_ex(MasterBridge.HostName)[2]
        ] + ["127.0.0.1",]

    def searchForWorker(self):
        workerLst = set()
        scanPack = bytes((0,ScanRequestTaskId,randint(0,255),0,0,0))

        self.__updateScanAddr()
        self.__mainDSkLane.settimeout(MasterBridge.LCInter)
        for _ in range(MasterBridge.RepeatScan):
            try:
                for nwAddr in MasterBridge.Nw2Scan:
                    self.__mainDSkLane.sendto(
                        scanPack,
                        (nwAddr, MasterBridge.MainPort)
                    )
                data,addr = self.__mainDSkLane.recvfrom(6)
                if data[:3]==scanPack[:3]:
                    workerLst.add(addr[0])
            except timeout:
                pass
        self.__mainDSkLane.settimeout(0)
        return workerLst

    def connectToWorker(self,ipAddr,taskManager=None):
        self.__workerAddr = (ipAddr, MasterBridge.MainPort)
        sndPack = bytearray((0,ConnectRequestTaskId,randint(0,255),0,0,0))

        try:
            self.__mainDSkLane.sendto(sndPack, self.__workerAddr)

            sndPack[1] = ConnectionTaskId; sndPack[3] = 1
            self.__mainDSkLane.settimeout(MasterBridge.LCInter)
            while True:
                data,addr = self.__mainDSkLane.recvfrom(6)
                if addr==self.__workerAddr and data[:4]== sndPack[:4]:
                    break
            self.__eDataSSkLane = socket(AF_INET, SOCK_STREAM)
            self.__eDataSSkLane.settimeout(MasterBridge.LCInter)
            self.__eDataSSkLane.connect((ipAddr, MasterBridge.DataPort))

            sndPack[3] = 2
            self.__eDataSSkLane.send(sndPack[:4] + (b"\x00" * 8))

            data = recvFull(self.__eDataSSkLane, 12)
            if len(data)!=12 or data[:4] != sndPack[:4]:
                raise ConnectionError("Can't establish connection")

            self.__isAlive = True
            print("Connected")
            self.__sndRecvThread = Thread(target=self.__sendRecvLooper,args=(taskManager,))
            self.__sndRecvThread.start()
        except timeout: self.disconnectWorker()
        except ConnectionError: self.disconnectWorker()


    # 0: 0.055, 0.25: 0.11, 0.5: 0.26, 0.75: 0.5
    def __sendRecvLooper(self,taskManager=None):
        beatBuf = bytes((0,BeatTaskId,0,0,0,0))
        nextReplyWithin = -1
        self.__mainDSkLane.settimeout(MasterBridge.InterBy4)

        self.__mainDSkLane.sendto(beatBuf, self.__workerAddr)
        while self.isConnected():
            try:
                data,addr = self.__mainDSkLane.recvfrom(MasterBridge.InitSize)
                if addr == self.__workerAddr:
                    nextReplyWithin = time() + MasterBridge.Inter
                    taskId = int.from_bytes(data[:2], 'big', signed=False)
                    if taskId == BeatTaskId: pass
                    elif taskId == DisconnectTaskId: break
                    elif taskId == ExtendedTaskId:
                        if taskManager is not None:
                            taskManager.handleExReplay(self.__eDataSSkLane)
                    else:
                        if taskManager is not None:
                            taskManager.handleReplay(
                                int.from_bytes(data[2:], 'big', signed=False),
                                data[2:6]
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

    def sendTask(self,taskId,data):
        if not self.isConnected():
            return
        sndBuf = int.to_bytes(taskId, 2, 'big', signed=False) + int.to_bytes(data, 4, 'big', signed=False)
        try:
            self.__mainDSkLane.sendto(sndBuf, self.__workerAddr)
            self.__nextBeatAt = time() + MasterBridge.InterBy4
        except IOError:
            pass

    def sendExTask(self,taskId,sendData):
        if not self.isConnected():
            return

        try:
            self.__eDataSSkLane.send(int.to_bytes(taskId, 2, 'big', signed=False))
            sendData(self.__eDataSSkLane)
            self.__mainDSkLane.sendto(bytes((0, ExtendedTaskId)), self.__workerAddr)
            self.__nextBeatAt = time() + MasterBridge.InterBy4
        except IOError:
            pass

    def recvExReplay(self,size):
        return self.__eDataSSkLane.recv(size)

    def disconnectWorker(self):
        if self.__workerAddr is None:
            return

        if self.__eDataSSkLane is not None:
            self.__eDataSSkLane.close()
            self.__eDataSSkLane = None

        if self.__isAlive:
            self.__isAlive = False
            if self.__sndRecvThread is not None and current_thread() != self.__sndRecvThread:
                self.__sndRecvThread.join()
            # if self.__sndRecvThread is not None and current_thread() != self.recvThread:
            #     self.recvThread.join()
            self.__workerAddr = None
            print("Disconnected")

    def disconnectFromWorker(self):
        if not self.isConnected():
            return
        self.__mainDSkLane.sendto(bytes((0, DisconnectTaskId, 0, 0, 0, 0)), self.__workerAddr)
        self.disconnectWorker()