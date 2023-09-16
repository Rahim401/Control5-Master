import struct
from ipaddress import ip_address
from socket import socket

def toBcAddress(ip,mask):
    octet = [int(pr) for pr in ip.split('.') if pr.isdigit()]
    if len(octet)!=4:
        return

    tempMaskByte = 0
    for i in range(32):
        movVal = i%8
        tempMaskByte |= 2 ** (7 - movVal)
        if movVal==7:
            octet[i//8] = str(octet[i//8] | tempMaskByte)
            tempMaskByte = 0
    return '.'.join(octet)

def recvFull(sk:socket,sz):
    toRead = sz
    buf = b""
    while toRead>0:
        buf += sk.recv(toRead)
        toRead = sz - len(buf)
    return buf

def sendString(sk:socket,string:str):
    encText = string.encode()
    sk.send(int.to_bytes(len(encText), 2, 'big'))
    sk.send(encText)

def recvString(sk:socket):
    strSz = int.from_bytes(recvFull(sk,2),'big',signed=True)
    decStr = recvFull(sk,strSz).decode()
    return decStr

def readUTF(arr:bytearray,at):
    strSz = int.from_bytes(arr[at:at+2],'big',signed=True)
    decStr = arr[at+2:at+2+strSz].decode()
    return decStr


class ByteBuffer(bytearray):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.__pointerPos = 0

    def clear(self) -> None:
        super().clear()
        self.__pointerPos = 0

    def putBytes(self,data,idx=-1):
        isUsingReadPos = idx==-1
        if isUsingReadPos: idx = self.__pointerPos
        if idx < 0 or idx >= len(self):
            self.extend(data)
        else:
            for i,byt in enumerate(data,idx):
                if i<len(self): self[i] = byt
                else: self.append(byt)
        if isUsingReadPos:
            self.__pointerPos += len(data)

    def putShort(self,num,idx=-1):
        self.putBytes(int.to_bytes(num,2,byteorder='big',signed=False),idx)

    def putInt(self,num,idx=-1):
        self.putBytes(int.to_bytes(num,4,byteorder='big',signed=False),idx)

    def putLong(self,num,idx=-1):
        self.putBytes(int.to_bytes(num,8,byteorder='big',signed=False),idx)

    def putUTF(self,msg:str,idx=-1):
        msgArr = msg.encode()
        self.putShort(len(msgArr),idx)
        if idx >= 0: idx += 2
        self.putBytes(msgArr,idx)

    def setPointerPos(self,pos):
        self.__pointerPos = pos

    def getBytes(self,sz,idx=-1):
        isUsingReadPos = idx==-1
        if isUsingReadPos: idx = self.__pointerPos
        if idx+sz > len(self):
            raise IndexError("list index and size out of range")
        if isUsingReadPos: self.__pointerPos += sz
        return self[idx:idx+sz]

    def getShort(self,idx=-1):
        return int.from_bytes(
            self.getBytes(2,idx),
            byteorder='big',signed=False
        )

    def getInt(self,idx=-1):
        return int.from_bytes(
            self.getBytes(4,idx),
            byteorder='big',signed=False
        )

    def getLong(self,idx=-1):
        return int.from_bytes(
            self.getBytes(8,idx),
            byteorder='big',signed=False
        )

    def getUTF(self,idx=-1):
        msgSz = self.getShort(idx)
        if idx >= 0: idx += 2
        return self.getBytes(msgSz,idx).decode()

    @staticmethod
    def makeBuffer(**kwargs):
        Bf = ByteBuffer()
        for key,value in kwargs.items():
            # if key[0]=="u":
            #     key=key[1:]
            #     Sign = False
            if key.startswith("Byt"): Bf.append(value)
            elif key.startswith("Sht"): Bf.putShort(value)
            elif key.startswith("Int"): Bf.putInt(value)
            elif key.startswith("Bts"): Bf.putBytes(value)
            elif key.startswith("Str"): Bf.putUTF(value)
            elif key.startswith("Lng"): Bf.putLong(value)
            # elif key.startswith("Flt"): Bf.putFloat(value)
            # elif key.startswith("Dbl"): Bf.putDouble(value)
            else: raise AttributeError(f"Invalid key {key}.\nValid Keys should start with : Byt,Sht,Int,Lng,Flt,Dbl,Chr,Str")
        return Bf

if __name__=="__main__":
    x = ByteBuffer()
    x.putBytes(b"He;llo",3)
    x.putBytes(b"hi",1)
    x.putShort(21,5)
    x.putUTF("Vanakam di mappilacgdytd6rf fuck u da",3)
    print(x.getBytes(5))
    print(x.getBytes(32))
    x.setPointerPos(5)
    x.putUTF("312121")
    print(x)