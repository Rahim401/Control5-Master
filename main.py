from Bridge import MasterBridge

brg = MasterBridge()
brg.connectToWorker("192.168.43.1")

while brg.isConnected():
    try:
        task = int(input("Enter task to Perform: "))
        if task==10:
            break
        brg.sendData(task,127)
    except ValueError: pass
    except OverflowError: pass

brg.disconnectFromWorker()