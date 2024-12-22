import asyncio
import ConferenceServer as ConferenceServer
from util import *

class TextMessageProtocol(asyncio.DatagramProtocol):
    def __init__(self, server: ConferenceServer):
        self.server = server

    def connection_made(self, transport):
        self.transport = transport
        print("TextMessageProtocol connection has been established.")

    def datagram_received(self, data, addr):
        # self.server.add_client(addr)
        try:
            header = data[:5].decode()
            payload = data[5:].decode()
            if header == "TEXT ":
                print('receive mes')
                self.server.broadcast_message(payload, addr)
        except Exception as e:
            print(f"Error occurs when receiving from {addr}: {e}")

    def error_received(self, exc):
        print(f"TextMessageProtocol received an error: {exc}")

    def connection_lost(self, exc):
        print("TextMessageProtocol connection has been lost.")




class RTPProtocol(asyncio.DatagramProtocol):
    def __init__(self, server: ConferenceServer, data_type: str):
        self.server = server
        self.data_type = data_type

    def connection_made(self, transport):
        self.transport = transport
        print(f"{self.data_type.capitalize()} RTPProtocol has been established.")

    def datagram_received(self, data, addr):
        # self.server.add_client(addr)
        if self.data_type == 'video':
            self.server.handle_video_frame(data)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                return
        elif self.data_type == 'audio':
            self.server.handle_audio_data(data)
        # TODO:
        self.server.forward_rtp_data(data, addr, self.data_type)

    def error_received(self, exc):
        print(f"{self.data_type.capitalize()} RTPProtocol 接收到错误: {exc}")

    def connection_lost(self, exc):
        print(f"{self.data_type.capitalize()} RTPProtocol 连接已关闭。")