from ipaddress import ip_address

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