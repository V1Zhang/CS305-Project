import asyncio
from util import *
import socket
import time
import threading
import struct
import config
import matplotlib.pyplot as plt
from Protocols import TextMessageProtocol
from Protocols import RTPProtocol



class ConferenceServer:
    # 客户与会议服务器之间的通信协议应该基于连接，需要多个端口
    def __init__(self,conference_id):
        # async server
        self.conference_id = conference_id  # conference_id for distinguish difference conference
        # 绑定端口
        self.udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udpSocket.bind(('0.0.0.0',0))
        self.udp_port = self.udpSocket.getsockname()[1]

        self.audio_rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.audio_rtpSocket.bind(('0.0.0.0',0))
        self.audio_rtp_port = self.audio_rtpSocket.getsockname()[1]

        self.video_rtpSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.video_rtpSocket.bind(('0.0.0.0',0))
        self.video_rtp_port = self.video_rtpSocket.getsockname()[1]

        self.rtcpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtcpSocket.bind(('0.0.0.0',0))
        self.rtcp_port = self.rtcpSocket.getsockname()[1]
        
        self.conf_serve_ports = None
        self.data_serve_ports = {}
        self.data_types = ['screen', 'camera', 'audio']  # example data types in a video conference
        self.clients_info = []  # (address, port) for each client
        self.client_conns = None
        self.host_address = None
        self.mode = 'Client-Server'  # or 'P2P' if you want to support peer-to-peer conference mode

        self.P = pyaudio.PyAudio()
        self.audio_stream = self.P.open(format=pyaudio.paInt16,
                                        channels=1,
                                        rate=44100,
                                        output=True,
                                        frames_per_buffer=2048)
    async def handle_data(self, reader, writer, data_type):
        """
        running task: receive sharing stream data from a client and decide how to forward them to the rest clients
        """
        # timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())




    async def handle_client(self, reader, writer):
        """
        running task: handle the in-meeting requests or messages from clients
        """
        

    

    async def log(self):
        while self.running:
            print('Something about server status')
            await asyncio.sleep(LOG_INTERVAL)

    async def cancel_conference(self):
        """
        handle cancel conference request: disconnect all connections to cancel the conference
        """
    
    def broadcast_message(self,message,sender_address):
        """
        Broadcast text messages to all connected clients except the sender.
        """
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        formatted_message = f"[{timestamp}] {sender_address}: {message}"
        broadcast_data = encode_message("TEXT ",self.udp_port,formatted_message)
        print(f"Broadcasting message: {formatted_message}")
        for client in self.clients_info:
            if client != sender_address:
                try:
                    self.udpSocket.sendto(broadcast_data,client)
                    print("Message sent.")
                except Exception as e:
                    print(f"Error sending message to {client}: {e}")

    def broadcast_info(self,info,error):
        """
        Broadcast text messages to all connected clients: Someone is added to the conference, the conference is cloesd, etc.
        """
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        formatted_message = f"[{timestamp}]: {info}"
        if error == BROADCAST_JOIN:
            broadcast_data = encode_message("TEXT ",self.udp_port,formatted_message)
        elif error == BROADCAST_CANCEL_CONFERENCE:
            broadcast_data = encode_message("CANCL",self.udp_port,formatted_message)
        print(f"Broadcasting message: {formatted_message}")
        for client in self.clients_info:
                try:
                    self.udpSocket.sendto(broadcast_data,client)
                    print("Message sent.")
                except Exception as e:
                    print(f"Error sending message to {client}: {e}")

    
    async def start(self):
        '''
        start the ConferenceServer and necessary running tasks to handle clients in this conference
        '''
        print(f"Conference {self.conference_id} server is ready to receive.")
        loop = asyncio.get_event_loop()

        # 创建用于处理文本消息的UDP端点
        self.text_transport, self.text_protocol = await loop.create_datagram_endpoint(
            lambda: TextMessageProtocol(self),
            local_addr=('127.0.0.1',self.udp_port)  
        )
        print(f"Text data is handled on port {self.udp_port}.")
        # 创建用于处理音频 RTP 流的 UDP 端点
        self.audio_transport, self.audio_protocol = await loop.create_datagram_endpoint(
            lambda: RTPProtocol(self, 'audio'),
            local_addr=('127.0.0.1', self.audio_rtp_port)
        )
        print(f"Audio data is handled on port {self.audio_rtp_port}.")

        # 创建用于处理视频 RTP 流的 UDP 端点
        self.video_transport, self.video_protocol = await loop.create_datagram_endpoint(
            lambda: RTPProtocol(self, 'video'),
            local_addr=('127.0.0.1', self.video_rtp_port)
        )
        print(f"Video data is handled on port {self.video_rtp_port}.")

        try:
            await asyncio.Future()  # 运行直到被手动停止
        except asyncio.CancelledError:
            pass
        finally:
            self.close()
        
    def forward_rtp_data(self, data, sender_address, data_type):
        """
        Forward RTP packets
        """
        # TODO
        for client in self.clients_info:
            if client != sender_address:
                try:
                    if data_type == 'audio':
                        transport = self.audio_transport
                        header_bytes = "AUDIO".encode()
                        port_bytes = struct.pack('>H', self.audio_rtp_port)
                        data = header_bytes + port_bytes + data
                    elif data_type == 'video':
                        transport = self.video_transport
                        header_bytes = "VIDEO".encode()
                        port_bytes = struct.pack('>H', self.video_rtp_port)
                        data = header_bytes + port_bytes + data
                    else:
                        continue
                    transport.sendto(data, client)
                    print(f"{data_type.capitalize()} RTP packets are sent to {client}")
                except Exception as e:
                    print(f"向 {client} 发送 {data_type} RTP 数据包时出错: {e}")

    def handle_video_frame(self, data):
        """
        Decode Video Frame
        """
        # 解码图像
        # frame_data = np.frombuffer(data, dtype='uint8')
        # img = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
        # if img is not None:
        #     # 在图像上叠加“server”字样
        #     cv2.putText(img, "server", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        #     # 使用 matplotlib 显示图像
        #     if self.im_display is None:
        #         self.im_display = self.ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        #         self.fig.canvas.draw()
        #         self.fig.canvas.flush_events()
        #     else:
        #         self.im_display.set_data(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        #         self.fig.canvas.draw()
        #         self.fig.canvas.flush_events()
        #     print("Video data is received.")
        frame_data = np.frombuffer(data, dtype='uint8')
        img = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
        # if img is not None:
        #                 # 在图像上显示“server”字样
        #     cv2.putText(img, "server", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        #     cv2.imshow('server', img)
    def handle_audio_data(self, data):
        """
        播放从客户端接收的音频数据
        """
        self.audio_stream.write(data)
        print("Audio Data Received")

    def close(self):
        """
        关闭服务器并清理资源
        """
        self.text_transport.close()
        self.audio_transport.close()
        self.video_transport.close()
        self.audio_stream.stop_stream()
        self.audio_stream.close()
        self.P.terminate()
        plt.close(self.fig)
        print(f"Conference Server {self.conference_id} is closed.")
