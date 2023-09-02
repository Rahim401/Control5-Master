from time import sleep,time
from Bridge import MasterBridge,TaskManager

def sendString(st,string:str):
    encText = string.encode()
    st.send(int.to_bytes(len(encText),2,'big'))
    st.send(encText)

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
        print("\rGot Replay",replayId,data,end="\nEnter Data: ")

    def handleExReplay(self):
        print("\rGot ExReplay",self.__brg.recvExReplay(10000),end="\nEnter Data: ")

    def echoInt(self,data):
        self.__brg.sendTask(512, int(data))

    def echoString(self,data):
        self.__brg.sendExTask(513,lambda stream: sendString(stream, data))

if __name__ == "__main__":
    ctrl = Control("127.0.0.1")
    ctrl.connect()

    while ctrl.isConnected():
        data = input("Enter Data: ")
        ctrl.echoString(data)
