from btmesh.Context import *
from btmesh.Util import *
from btmesh.Message import *

netkeys = [
    NetworkKey.fromString(
        '27D03FD339A0ED2B35159A97DEE5BCA9', iv_index=0, tag='network')
]

appkeys = [
    ApplicationKey.fromString(
        '354242690103C7D7271B8D01AF58297F', iv_index=738, tag='Generic'),
    ApplicationKey.fromString(
        'FCB937EAE46DFF7E04DE63C08746F5CA', iv_index=663, tag='Setup'),
    ApplicationKey.fromString(
        '5ECB8B26A3B24130B4F088DD701FD929', iv_index=3720, tag='Vendor'),
]


devkeys = [
    DeviceKey.fromString(
        '1FFCC17C6411835164769DF36BF8AE01', nodeid=2),
    DeviceKey.fromString(
        '5ABD9DC7F2C43CBE335D47501E04A23F', nodeid=4),
    DeviceKey.fromString(
        'DDD0035D1D3AC520E8031700C812BC82', nodeid=6),
]


def toStr(s):
    return ' '.join(map('{:02x}'.format, s))


def PayloadDecode(s):
    total_len = len(s)
    i = 0
    packet_list = list()
    while i < total_len:
        packet_len = s[i]
        packet_type = s[i+1]
        packet_payload = s[i+2:i+packet_len+1]
        i += packet_len+1
        packet_list.append((packet_type, packet_payload))

    if i != total_len:
        print(s.hex())
        print('i != total_len')
    return packet_list


with MeshContext(netkeys=netkeys, appkeys=appkeys, devicekeys=devkeys) as ctx:
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('192.168.113.250', 10010))
    f = sock.makefile()
    while True:
        l = f.readline()
        rssi, addr, data = eval(l)
        addr = Addr(addr)
        payloads = None
        try:
            payloads = PayloadDecode(data)
        except IndexError:
            # print(rssi, addr, data.hex())
            continue
        for payload in payloads:
            packet = AdvertisingMessage.from_bytes(payload)
            if isinstance(packet, MeshMessage):
                # print(rssi, addr)
                ctx.decode_message(packet)
            elif isinstance(packet, MeshBeacon):
                pass
