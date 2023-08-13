

from time import sleep,time
from utils import toBcAddress
from random import randbytes,randint
from threading import Thread,current_thread
from socket import socket,AF_INET,SOCK_DGRAM,SOCK_STREAM,timeout
from socket import getaddrinfo,gethostname,getnameinfo,if_nameindex,gethostbyname_ex,gethostbyname

class MasterBridge:
    MainPort = 32654
    HostName = gethostname()
    Nw2Scan = ()

    RepeatScan = 10
    InitSize = 64
    Inter = 1
    InterBy4 = Inter / 4

    def __init__(self):
        self.mainSkLane = socket(AF_INET,SOCK_DGRAM)
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
        scanPack = bytes((0,0,randint(0,255),0,0))

        self.updateScanAddr()
        self.mainSkLane.settimeout(0.1)
        for _ in range(MasterBridge.RepeatScan):
            try:
                for nwAddr in MasterBridge.Nw2Scan:
                    self.mainSkLane.sendto(
                        scanPack,
                        (nwAddr, MasterBridge.MainPort)
                    )
                data,addr = self.mainSkLane.recvfrom(MasterBridge.InitSize)
                if data[:3]==scanPack[:3]:
                    workerLst.add(addr[0])
            except timeout:
                pass
        self.mainSkLane.settimeout(0)
        return workerLst

    def connectToWorker(self,ipAddr):
        sndPack = bytes((0,8,randint(0,255),0))
        skAddr = (ipAddr,MasterBridge.MainPort)

        self.mainSkLane.sendto(sndPack,skAddr)
        self.mainSkLane.settimeout(MasterBridge.InterBy4)
        try:
            while True:
                data,addr = self.mainSkLane.recvfrom(MasterBridge.InitSize)
                if addr==skAddr and data[:3]==sndPack[:3] and data[3]==1:
                    break
        except timeout: return

        print("Connected")
        self.isAlive = True
        self.workerAddr = skAddr
        self.mainSkLane.sendto(b"\x00\x09\x00\x00\x00\x00", self.workerAddr)
        self.sndThread = Thread(target=self.sendLooper)
        self.sndThread.start()
        self.recvThread = Thread(target=self.recvLooper)
        self.recvThread.start()



    def sendLooper(self):
        beatBuf = b"\x00\x09\x00\x00\x00\x00"
        try:
            while self.isConnected():
                sleep(MasterBridge.InterBy4)
                now = time()
                if now > self.nextBeatAt:
                    self.mainSkLane.sendto(beatBuf,self.workerAddr)
                    self.nextBeatAt = now + MasterBridge.InterBy4
        except IOError: pass
        self.disconnectWorker()

    def sendData(self,taskId,data):
        if not self.isConnected():
            return
        sndBuf = int.to_bytes(taskId, 2, 'big', signed=False) + int.to_bytes(data, 4, 'big', signed=False)
        try:
            self.mainSkLane.sendto(sndBuf, self.workerAddr)
            self.nextBeatAt = time() + MasterBridge.InterBy4
        except IOError:
            pass


    def recvLooper(self):
        try:
            self.mainSkLane.settimeout(MasterBridge.Inter)
            lastReplayAt = -1
            while self.isConnected():
                data,addr = self.mainSkLane.recvfrom(MasterBridge.InitSize)
                if addr==self.workerAddr:
                    now = time()
                    # print("Delay",now - lastReplayAt)
                    lastReplayAt = now

                    taskId = int.from_bytes(data[:2],'big',signed=False)
                    if taskId == 10:
                        break
        except timeout: pass
        self.disconnectWorker()


    def disconnectWorker(self):
        if not self.isConnected():
            return

        self.isAlive = False
        if current_thread() != self.sndThread:
            self.sndThread.join()
        if current_thread() != self.recvThread:
            self.recvThread.join()
        print("Disconnected")
        self.workerAddr = None

    def disconnectFromWorker(self):
        if not self.isConnected():
            return
        self.mainSkLane.sendto(b"\x00\x0A\x00\x00\x00\x00",self.workerAddr)
        self.disconnectWorker()