import eventlet
eventlet.monkey_patch()
import asyncio
from util import *
import socket
import time
import threading
import struct
import config
import matplotlib.pyplot as plt
import RtpPacket
from conf_server import ConferenceServer
from Protocol import TextMessageProtocol, RTPProtocol
import socketio
import base64
from werkzeug.serving import WSGIRequestHandler
import logging
import sys
import os

class MainServer:
    def __init__(self, server_ip, main_port):
        # async server
        self.server_ip = server_ip
        self.server_port = main_port
        self.main_server = None

        self.conference_conns = None
        self.conference_servers = {}
        self.clients = []
        self.threads = {}
        # build socket
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.serverSocket.bind((server_ip, main_port))
        self.P=pyaudio.PyAudio()
        self.audio_stream = self.P.open(format=pyaudio.paInt16,channels=1, rate=44100,output=True,frames_per_buffer=2048)
        

        # SocketIO server
        # create a Socket.IO servers
        
        self.sio = socketio.Server(async_mode='eventlet',cors_allowed_origins="http://localhost:5173",
                                   ping_interval=10, ping_timeout=20 ,
                                   max_http_buffer_size=10000000,
                                   logger=False,  # 禁用 Flask-SocketIO 的日志输出
                                   engineio_logger=False  # 禁用 Engine.IO 的日志输出
                                   )

        self.app = socketio.Middleware(self.sio)
        self.register_socketio_events()
        eventlet.wsgi.server(eventlet.listen(('', 7000)), self.app)
        
       # 禁用 werkzeug 的 HTTP 请求日志
        WSGIRequestHandler.log_request = lambda *args, **kwargs: None

        # 禁用 logging
        logging.getLogger('werkzeug').setLevel(logging.CRITICAL)
        logging.getLogger('werkzeug').handlers = []

        # 重定向标准输出和错误输出
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        
        
        
        # self.p = pyaudio.PyAudio()
        # self.audio_stream = self.p.open(format=pyaudio.paInt16,  # 16-bit audio format
        #                     channels=1,              # 单声道
        #                     rate=44100,              # 采样率
        #                     output=True,             # 输出模式
        #                     frames_per_buffer=2048)  # 缓冲区大小

         # Register SocketIO event
        
        print('The server is ready to receive')
        # plt.ion()
        # self.fig, self.ax = plt.subplots()
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


    def handle_quit_conference(self,conference_id):
        """
        quit conference (in-meeting request & or no need to request)
        """
        try:
            conference = self.conference_servers.get(conference_id)
            if not conference:
                print(f"Conference ID {conference_id} not found.")
                return

            # 通知所有与会者会议结束
            for client in conference.clients_info:
                try:
                    message = f"Conference {conference_id} has ended."
                    data = message.encode()
                    self.udpSocket.sendto(data, client)
                    print(f"Notified {client} about conference ending.")
                except Exception as e:
                    print(f"Error notifying client {client}: {e}")

            # 关闭所有与会者的线程并释放资源
            for client in conference.clients_info:
                self.release_client_resources(client)

            # 删除会议对象
            del self.conference_servers[conference_id]
            print(f"Conference {conference_id} has been successfully ended and resources released.")

        except Exception as e:
            print(f"Error ending conference {conference_id}: {e}")
        
    def handle_leave_conference(self, conference_id, client_address):
        """
        Handle a single client leaving the conference. If the conference becomes empty, end it.
        """
        try:
            conference = self.conference_servers.get(conference_id)
            if not conference:
                print(f"Conference ID {conference_id} not found.")
                return

            # 移除客户端
            if client_address in conference.clients_info:
                conference.clients_info.remove(client_address)
                print(f"Client {client_address} has left conference {conference_id}.")
            else:
                print(f"Client {client_address} not found in conference {conference_id}.")

            # 通知其他与会者（可选）
            for other_client in conference.clients_info:
                try:
                    message = f"Client {client_address} has left the conference."
                    data = message.encode()
                    self.Socket.sendto(data, other_client)
                    print(f"Notified {other_client} about {client_address} leaving.")
                except Exception as e:
                    print(f"Error notifying client {other_client}: {e}")

            # 检查会议是否为空
            if len(conference.clients_info) == 0:
                print(f"No clients remaining in conference {conference_id}. Ending conference.")
                self.handle_quit_conference(conference_id)

        except Exception as e:
            print(f"Error handling client {client_address} leaving conference {conference_id}: {e}")

    def release_client_resources(self, client_address):
        """
        Release resources associated with a client.
        """
        try:
            if client_address in self.client_threads:
                client_thread = self.client_threads.pop(client_address, None)
                if client_thread and client_thread.is_alive():
                    client_thread.join(timeout=1)  # 等待线程退出
                    print(f"Thread for client {client_address} terminated.")
            else:
                print(f"No active thread found for client {client_address}.")
        except Exception as e:
            print(f"Error releasing resources for client {client_address}: {e}")

        

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
                data, client_address = self.serverSocket.recvfrom(1024)
                if not data:
                    continue
                header, payload = data[:5].decode(), data[5:]  # 协议头为固定长度5字节
                # print(header)
                if client_address not in self.clients:
                    print(client_address)
                    self.clients.append(client_address)
                
                if header == "TEXT ":
                    message = payload.decode()
                    self.broadcast_message(message, client_address)
                elif header == "VIDEO":   
                    # 解码接收到的图像数据
                    frame_data = np.frombuffer(payload, dtype='uint8')
                elif header == "AUDIO":
                    self.audio_stream.write(payload)
                    print("Audio data received .")
                elif header == "SHARE":   
                    # 解码接收到的图像数据
                    frame_data = np.frombuffer(payload, dtype='uint8')
                elif header == "CREAT":
                    message = payload.decode()
                    print(f"Create conference {message} request received.")
                    self.handle_create_conference(conference_id=int(message),conference_host_address=client_address)
                    reply = f"You have been assigned to conference {message}"
                    print(self.conference_servers[int(message)].udp_port)
                    self.serverSocket.sendto(encode_message("TEXT ",self.conference_servers[int(message)].udp_port,reply), client_address)
                    port_message = f"{self.conference_servers[int(message)].audio_rtp_port} {self.conference_servers[int(message)].video_rtp_port} {self.conference_servers[int(message)].screen_rtp_port}"
                    self.serverSocket.sendto(encode_message("CREAT", self.conference_servers[int(message)].udp_port,port_message),client_address)
                elif header == "JOIN ":
                    message = payload.decode()
                    print(f"Join conference {message} request received.")
                    flag = self.handle_join_conference(conference_id=int(message))
                    if flag:
                        reply = f"OK:{message}"
                        self.serverSocket.sendto(encode_message("JOIN ", self.conference_servers[int(message)].udp_port, reply), client_address)
                        self.conference_servers[int(message)].clients_info.append(client_address)
                        port_message = f"{self.conference_servers[int(message)].audio_rtp_port} {self.conference_servers[int(message)].video_rtp_port} {self.conference_servers[int(message)].screen_rtp_port}"
                        self.serverSocket.sendto(encode_message("CREAT", self.conference_servers[int(message)].udp_port,port_message),client_address)
                        self.conference_servers[int(message)].broadcast_info(f"{client_address} has joined the conference.",BROADCAST_JOIN)
                    else:
                        reply = f"NK:{message}"
                        self.serverSocket.sendto(encode_message("JOIN ", self.server_port, reply), client_address)
                elif header == "QUIT ":
                    message = payload.decode()
                    print(f"Quit conference {message} request received.")
                    self.handle_quit_conference(conference_id=int(message))
                elif header == "LEAVE":
                    message = payload.decode()
                    print(f"Leave conference {message} request received.")
                    self.handle_leave_conference(conference_id=int(message),client_address=client_address)

                # # 按下 'q' 键退出
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            

            except Exception as e:
                print(f"Error: {e}")
                break
        
        self.serverSocket.close()
        cv2.destroyAllWindows()

    # sio 方法
    def register_socketio_events(self):
        """Define Socket.IO event handlers."""

        @self.sio.event
        def connect(sid, environ):
            # 从请求头中提取查询字符串
            query_string = environ.get("QUERY_STRING", "")
            params = dict(item.split("=") for item in query_string.split("&") if "=" in item)
            room = params.get("room")  # 获取房间号参数
            if room:
                self.sio.enter_room(sid, room)  # 将客户端加入指定房间
                print(f"Client {sid} connected and joined room {room}")
                # self.sio.emit("room_joined", {"message": f"Joined room {room}"}, room=sid)
            else:
                print(f"Client {sid} connected without specifying a room")
                # self.sio.emit("error", {"message": "Room not specified"}, room=sid)
        @self.sio.event
        def join_room(sid, data):
            room = data.get('room')
            if room:
                self.sio.enter_room(sid, room)
                print(f"Client {sid} joined room {room}")
                # self.sio.emit('room_joined', {'message': f'Joined room {room}'}, room=sid)
            else:
                print('error')
                # self.sio.emit('error', {'message': 'Room not specified'}, room=sid)


        @self.sio.event
        def disconnect(sid):
            print(f"Client {sid} disconnected.")

        @self.sio.on('create_conference')
        async def handle_create_conference(sid, data):
            conference_id = data.get('conference_id')
            if conference_id in self.conference_servers:
                await self.sio.emit('error', {'message': f'Conference {conference_id} already exists.'}, to=sid)
                return
            
            conference_server = ConferenceServer(conference_id=conference_id)
            self.conference_servers[conference_id] = conference_server
            conference_server.clients_info.append(sid)

            # Run ConferenceServer in a separate thread
            conference_thread = threading.Thread(target=self.run_conference_server, args=(conference_server,))
            conference_thread.start()
            self.threads[conference_id] = conference_thread

            print(f"Conference {conference_id} created by {sid}.")
            await self.sio.emit('conference_created', {'conference_id': conference_id}, to=sid)

        @self.sio.on('join_conference')
        async def handle_join_conference(sid, data):
            conference_id = data.get('conference_id')
            if conference_id not in self.conference_servers:
                await self.sio.emit('error', {'message': f'Conference {conference_id} not found.'}, to=sid)
                return

            self.conference_servers[conference_id].clients_info.append(sid)
            print(f"Client {sid} joined conference {conference_id}.")
            await self.sio.emit('joined_conference', {'conference_id': conference_id}, to=sid)

        @self.sio.on('get_available_conferences')
        def get_available_conferences(sid):
            try:
                conferences = [conference_id for conference_id, server in self.conference_servers.items()]
                self.sio.emit('available_conferences', {"status": "success", "conferences": conferences })
            except Exception as e:
                self.sio.emit('available_conferences', {"status": "error", "message": str(e)})


        @self.sio.on('text_message')
        async def handle_text_message(sid, data):
            message = data.get('message')
            room = data.get('room')
            if room not in self.conference_servers:
                await self.sio.emit('error', {'message': f'Conference {room} not found.'}, to=sid)
                return

            formatted_message = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {sid}: {message}"
            await self.sio.emit('text_message', {'message': formatted_message}, room=room)
            print(f"Broadcasted message: {formatted_message}")
        
        @self.sio.on('video_frame')
        def handle_video_frame(sid, data):
            """
            Handle incoming video frames and broadcast to all other clients.
            """
            room = data.get("room")
            frame_with_sender = {
                'frame': data['frame'],
                'sender_id': data['sender_id']  # Use the Socket.IO sid as the sender identifier
            }
            print(data['sender_id'])
            self.sio.emit('video_frame', frame_with_sender,room=room)
            
        @self.sio.on('screen_frame')
        def handle_screen_share(sid, data):
            """
            Handle incoming screen share frames and broadcast to all other clients.
            """
            room = data.get("room")
            frame_with_sender = {
                'frame': data['frame'],
                'sender_id': sid  # Use the Socket.IO sid as the sender identifier
            }
            self.sio.emit('screen_frame', frame_with_sender,room=room)


        @self.sio.on('audio_stream')
        def handle_audio_stream(sid,data):
            # audio_data = base64.b64decode(data)
            room = data.get("room")
            data = data.get("data")
            self.sio.emit('audio_stream', data,room=room)
            
        @self.sio.on('heartbeat')  # 自定义心跳事件
        def heartbeat(sid, data):
            print(f'Heartbeat from {sid}: {data}')
            self.sio.emit('heartbeat_response', {'status': 'ok'}, to=sid)


if __name__ == '__main__':
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT)
    server.start()