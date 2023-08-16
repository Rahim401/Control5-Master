

from time import sleep,time
from utils import toBcAddress,recvFull
from random import randbytes,randint
from threading import Thread,current_thread
from socket import socket,AF_INET,SOCK_DGRAM,SOCK_STREAM,timeout,MSG_WAITALL
from socket import getaddrinfo,gethostname,getnameinfo,if_nameindex,gethostbyname_ex,gethostbyname

class MasterBridge:
    MainPort = 32654
    DataPort = MainPort+1
    HostName = gethostname()
    Nw2Scan = ()

    RepeatScan = 10
    InitSize = 64
    Inter = 1
    InterBy4 = Inter / 4

    def __init__(self):
        self.mainDSkLane = socket(AF_INET, SOCK_DGRAM)
        self.dataSSkLane = None
        self.isAlive = False
        self.workerAddr = None

        self.sndThread = None
        self.recvThread = None

        self.nextBeatAt = -1

    def isConnected(self):
        return self.isAlive

    def updateScanAddr(self):
        MasterBridge.Nw2Scan = [
            ip[:ip.rfind('.')]+".255" for ip in gethostbyname_ex(MasterBridge.HostName)[2]
        ]

    def searchForWorker(self):
        workerLst = set()
        scanPack = bytes((0,0,randint(0,255),0,0,0))

        self.updateScanAddr()
        self.mainDSkLane.settimeout(0.1)
        for _ in range(MasterBridge.RepeatScan):
            try:
                for nwAddr in MasterBridge.Nw2Scan:
                    self.mainDSkLane.sendto(
                        scanPack,
                        (nwAddr, MasterBridge.MainPort)
                    )
                data,addr = self.mainDSkLane.recvfrom(6)
                if data[:3]==scanPack[:3]:
                    workerLst.add(addr[0])
            except timeout:
                pass
        self.mainDSkLane.settimeout(0)
        return workerLst

    def connectToWorker(self,ipAddr):
        self.workerAddr = (ipAddr, MasterBridge.MainPort)
        sndPack = bytearray((0,8,randint(0,255),0,0,0))

        try:
            self.mainDSkLane.sendto(sndPack, self.workerAddr)

            sndPack[3] = 1
            self.mainDSkLane.settimeout(MasterBridge.InterBy4)
            while True:
                data,addr = self.mainDSkLane.recvfrom(6)
                if addr==self.workerAddr and data[:4]==sndPack[:4]:
                    break
            self.dataSSkLane = socket(AF_INET, SOCK_STREAM)
            self.dataSSkLane.settimeout(0.1)
            self.dataSSkLane.connect((ipAddr, MasterBridge.DataPort))

            sndPack[3] = 2
            self.dataSSkLane.send(sndPack[:4] + (b"\x00" * 8))

            data = recvFull(self.dataSSkLane,12)
            if len(data)!=12 or data[:4] != sndPack[:4]:
                raise ConnectionError("Can't establish connection")

            self.isAlive = True
            print("Connected")
            self.sndThread = Thread(target=self.sendLooper)
            self.sndThread.start()
            self.recvThread = Thread(target=self.recvLooper)
            self.recvThread.start()
        except timeout: self.disconnectWorker()
        except ConnectionError: self.disconnectWorker()




    def sendLooper(self):
        beatBuf = b"\x00\x09\x00\x00\x00\x00"
        try:
            while self.isConnected():
                sleep(MasterBridge.InterBy4)
                now = time()
                if now > self.nextBeatAt:
                    self.mainDSkLane.sendto(beatBuf, self.workerAddr)
                    self.nextBeatAt = now + MasterBridge.InterBy4
        except IOError: pass
        self.disconnectWorker()

    def sendData(self,taskId,data):
        if not self.isConnected():
            return
        sndBuf = int.to_bytes(taskId, 2, 'big', signed=False) + int.to_bytes(data, 4, 'big', signed=False)
        try:
            self.mainDSkLane.sendto(sndBuf, self.workerAddr)
            self.nextBeatAt = time() + MasterBridge.InterBy4
        except IOError:
            pass


    def recvLooper(self):
        try:
            self.mainDSkLane.settimeout(MasterBridge.Inter)
            lastReplayAt = -1
            while self.isConnected():
                data,addr = self.mainDSkLane.recvfrom(MasterBridge.InitSize)
                if addr==self.workerAddr:
                    now = time()
                    # print("Delay",now - lastReplayAt)
                    lastReplayAt = now

                    taskId = int.from_bytes(data[:2],'big',signed=False)
                    if taskId == 9: pass
                    elif taskId == 10:
                        break
                    else:
                        print(f"Got {taskId}",int.from_bytes(data[2:],'big',signed=False))
        except timeout: pass
        self.disconnectWorker()


    def disconnectWorker(self):
        if self.workerAddr is None:
            return

        if self.dataSSkLane is not None:
            self.dataSSkLane.close()
            self.dataSSkLane = None

        if self.isAlive:
            self.isAlive = False
            if self.sndThread is not None and current_thread() != self.sndThread:
                self.sndThread.join()
            if self.sndThread is not None and current_thread() != self.recvThread:
                self.recvThread.join()
            self.workerAddr = None
            print("Disconnected")

    def disconnectFromWorker(self):
        if not self.isConnected():
            return
        self.mainDSkLane.sendto(b"\x00\x0A\x00\x00\x00\x00", self.workerAddr)
        self.disconnectWorker()