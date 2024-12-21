import asyncio
from util import *
import socket
import time
import threading
import struct
import config
import matplotlib.pyplot as plt
import RtpPacket
from queue import Queue, Empty
from conf_server import ConferenceServer


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
        self.queues = {}  # 存储每个 addr 的队列
        self.queue_threads = {}  # 存储每个 addr 的处理线程
        self.lock = threading.Lock()  # 确保线程安全
        self.loop = asyncio.new_event_loop()

    def connection_made(self, transport):
        self.transport = transport
        print(f"{self.data_type.capitalize()} RTPProtocol has been established.")

    def datagram_received(self, data, addr):
        # asyncio.create_task(self.server.forward_rtp_data(data,addr,self.data_type))
        with self.lock:  # 确保线程安全地访问 queues 和 queue_threads
            if addr not in self.queues:
                # 创建一个新的队列
                self.queues[addr] = Queue(maxsize=10000)
                # 创建并启动一个新线程来处理队列
                thread = threading.Thread(target=self.process_queue, args=(addr,), daemon=True)
                self.queue_threads[addr] = thread
                thread.start()

        # 将数据放入对应的队列
        if self.queues[addr].full()==False:
            self.queues[addr].put(data)

        if self.data_type == 'video':
            # self.server.handle_video_frame(data)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                return
        elif self.data_type == 'audio':
            self.server.handle_audio_data(data)
