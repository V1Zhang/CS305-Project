import base64
import socket
from client import ConferenceClient
data = base64.b64encode(b'Hello, World!').decode('utf-8')
print(data)
data = data.encode('utf-8')
print(data)
decode = base64.b64decode(data)
print(decode.decode('utf-8'))

udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.bind(('0.0.0.0',0))
print(udp.getsockname())

