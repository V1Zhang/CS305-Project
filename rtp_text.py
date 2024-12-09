from rtp import RTP, Extension, PayloadType
from copy import deepcopy
from Client import RtpPacket

rtppkt = RtpPacket.RtpPacket()
rtppkt.encode(2, 0, 0 , 0, 1111, 1, 11, 0, "Hello World this is the best thing that ever happen to me")
print(rtppkt.payload)
print(rtppkt.version())
print(rtppkt.seqNum())
print(rtppkt.timestamp())
print(rtppkt.Marker())