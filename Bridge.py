

from time import sleep,time
from utils import toBcAddress
from random import randbytes,randint
from threading import Thread
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
        self.workerAddr = None

        self.sndThread = None
        self.recvThread = None

        self.nextBeatAt = -1

    def isConnected(self):
        return self.workerAddr is not None

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

        self.mainSkLane.settimeout(1)
        try:
            while True:
                data,addr = self.mainSkLane.recvfrom(MasterBridge.InitSize)
                if addr==skAddr and data[:3]==sndPack[:3] and data[3]==1:
                    break
                # print(data,addr,skAddr)
        except timeout: return

        print("Connected")
        self.workerAddr = skAddr
        self.sndThread = Thread(target=self.sendLooper)
        self.sndThread.start()
        self.recvThread = Thread(target=self.recvLooper)
        self.recvThread.start()



    def sendLooper(self):
        beatBuf = b"\x00\x09\x00\x00\x00"
        try:
            while self.isConnected():
                sleep(MasterBridge.InterBy4)
                now = time()
                if now > self.nextBeatAt:
                    self.mainSkLane.sendto(beatBuf,self.workerAddr)
                    self.nextBeatAt = now + MasterBridge.InterBy4
        except IOError: pass
        self.disconnectWorker()

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

        print("Disconnected")
        self.workerAddr = None






Brg = MasterBridge()
Brg.connectToWorker("192.168.43.1")
# sleep(100)
# Brg.searchForWorker()
# print(toBcAddress("127.0.0.1",1))