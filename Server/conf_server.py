import asyncio
from util import *
import socket
import time
import threading
import struct
import config
import matplotlib.pyplot as plt


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
        
        plt.ion()
        self.fig, self.ax = plt.subplots()
        self.im_display = None
        


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
            # if client != sender_address:
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
        if img is not None:
                        # 在图像上显示“server”字样
            cv2.putText(img, "server", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            cv2.imshow('server', img)
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

class MainServer:
    def __init__(self, server_ip, main_port):
        # async server
        self.server_ip = server_ip
        self.server_port = main_port
        self.main_server = None

        self.conference_conns = None
        self.conference_servers = {}  # self.conference_servers[conference_id] = ConferenceServer
        self.clients = []
        self.threads = {}
        # build socket
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.serverSocket.bind((server_ip, main_port))
        self.P=pyaudio.PyAudio()
        self.audio_stream = self.P.open(format=pyaudio.paInt16,channels=1, rate=44100,output=True,frames_per_buffer=2048)
        print('The server is ready to receive')
        plt.ion()
        self.fig, self.ax = plt.subplots()
        # while True:
        #     connectionSocket, clientAddress = self.serverSocket.accept()
        #     client_thread = threading.Thread(target=handle_client, args=(connectionSocket, clientAddress))
        #     client_thread.start()  # 启动线程


    def handle_create_conference(self,conference_id,conference_host_address):
        # TODO: 重复的conference id，将线程修改为异步并发
        """
        create conference: create and start the corresponding ConferenceServer, and reply necessary info to client
        """
        conference_server = ConferenceServer(conference_id=conference_id)
        self.conference_servers[conference_id] = conference_server
        conference_server.clients_info.append(conference_host_address)
        self.host_address = conference_host_address
        print(self.conference_servers)
        # Create a new thread for the conference_server
        conference_thread = threading.Thread(target=self.run_conference_server, args=(conference_server,))
        conference_thread.start()
        self.threads[conference_id] = conference_thread

    def run_conference_server(self, conference_server: ConferenceServer):
        """
        运行 ConferenceServer 的异步事件循环
        """
        try:
            asyncio.run(conference_server.start())
        except Exception as e:
            print(f"运行会议 {conference_server.conference_id} 时出错: {e}")
        
        


        

    def handle_join_conference(self, conference_id):
        """
        join conference: search corresponding conference_info and ConferenceServer, and reply necessary info to client
        """
        # 绑定客户端到指定的端口
        if conference_id not in self.conference_servers.keys():
            print(f"Conference {conference_id} not found.")
            return False
        else :
            print(f"Conference {conference_id} found.")
            return True


    def handle_quit_conference(self,conference_id,client_address):
        """
        quit conference (in-meeting request & or no need to request)
        """
        self.conference_servers[conference_id].clients_info.remove(client_address)
        # 如果已经没有人在会议中，则关闭会议
        if len(self.conference_servers[conference_id].clients_info) == 0:
            self.handle_cancel_conference(conference_id)
        

    def handle_cancel_conference(self,conference_id):
        """
        cancel conference (in-meeting request, a ConferenceServer should be closed by the MainServer)
        """
        self.conference_servers[conference_id].broadcast_info("The conference is closed.",BROADCAST_CANCEL_CONFERENCE)
        # self.threads[conference_id].join()
        # TODO: 关闭线程
        del self.conference_servers[conference_id]
        del self.threads[conference_id]
        # self.threads[conference_id].join()

        

    async def request_handler(self, reader, writer):
        """
        running task: handle out-meeting (or also in-meeting) requests from clients
        """
        pass

    def broadcast_message(self, message, sender_address):
        """
        Broadcast text messages to all connected clients except the sender.
        """
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        formatted_message = f"[{timestamp}] {sender_address}: {message}"
        broadcast_data = encode_message("TEXT ", self.server_port, formatted_message)
        print(f"Broadcasting message: {formatted_message}")
        for client in self.clients:
            # if client != sender_address:  # 不发送给消息发送者
                print(client)
                try:
                    self.serverSocket.sendto(broadcast_data, client)
                    print("Message sent.")
                except Exception as e:
                    print(f"Error sending message to {client}: {e}")



    def start(self):
        """
        start MainServer
        """
        while True:
            try:
                # 接收数据
                data, client_address = self.serverSocket.recvfrom(921600)
                if not data:
                    continue
                header, payload = data[:5].decode(), data[5:]  # 协议头为固定长度5字节
                # print(header)
                if client_address not in self.clients:
                    self.clients.append(client_address)
                
                if header == "TEXT ":
                    message = payload.decode()
                    self.broadcast_message(message, client_address)
                elif header == "VIDEO":   
                    # 解码接收到的图像数据
                    frame_data = np.frombuffer(payload, dtype='uint8')
                    img = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
                    if img is not None:
                        # 在图像上显示“server”字样
                        cv2.putText(img, "server", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                        cv2.imshow('server', img)
                elif header == "AUDIO":
                    self.audio_stream.write(payload)
                    print("Audio data received .")
                elif header == "CREAT":
                    message = payload.decode()
                    print(f"Create conference {message} request received.")
                    self.handle_create_conference(conference_id=int(message),conference_host_address=client_address)
                    reply = f"You have been assigned to conference {message}"
                    print(self.conference_servers[int(message)].udp_port)
                    self.serverSocket.sendto(encode_message("TEXT ",self.conference_servers[int(message)].udp_port,reply), client_address)
                    port_message = f"{self.conference_servers[int(message)].audio_rtp_port} {self.conference_servers[int(message)].video_rtp_port}"
                    self.serverSocket.sendto(encode_message("CREAT", self.conference_servers[int(message)].udp_port,port_message),client_address)
                elif header == "JOIN ":
                    message = payload.decode()
                    print(f"Join conference {message} request received.")
                    flag = self.handle_join_conference(conference_id=int(message))
                    if flag:
                        reply = f"OK:{message}"
                        self.serverSocket.sendto(encode_message("JOIN ", self.conference_servers[int(message)].udp_port, reply), client_address)
                        self.conference_servers[int(message)].clients_info.append(client_address)
                        port_message = f"{self.conference_servers[int(message)].audio_rtp_port} {self.conference_servers[int(message)].video_rtp_port}"
                        self.serverSocket.sendto(encode_message("CREAT", self.conference_servers[int(message)].udp_port,port_message),client_address)
                        self.conference_servers[int(message)].broadcast_info(f"{client_address} has joined the conference.",BROADCAST_JOIN)
                    else:
                        reply = f"NK:{message}"
                        self.serverSocket.sendto(encode_message("JOIN ", self.server_port, reply), client_address)
                elif header == "QUIT ":
                    message = payload.decode()
                    print(f"Quit conference {message} request received.")
                    self.handle_quit_conference(conference_id=int(message),client_address=client_address)


                # # 按下 'q' 键退出
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            

            except Exception as e:
                print(f"Error: {e}")
                break
        
            
        self.serverSocket.close()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    server = MainServer('192.168.56.1', 7000)
    server.start()
