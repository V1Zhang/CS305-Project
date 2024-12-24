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

# Configure mode for the server: CS/P2P -- 1/0
MODE = 0

class MainServer:
    def __init__(self, server_ip, main_port):
        # async server
        self.room_manager = {} # Record the mode of each room: 0 for P2P, 1 for CS
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
        

        # SocketIO server
        # create a Socket.IO servers
        
        self.sio = socketio.Server(async_mode='eventlet',cors_allowed_origins=["http://localhost:5173","http://127.0.0.1:7000","https://admin.socket.io"],
                                   ping_interval=10, ping_timeout=20 ,
                                   max_http_buffer_size=10000000
                                   )
        self.sio.instrument(auth={
            'username':'admin',
            'password':'123456'
        })

        self.app = socketio.Middleware(self.sio)
        self.register_socketio_events()
        eventlet.wsgi.server(eventlet.listen(('', 7000)), self.app)
    
        
        print('The server is ready to receive')


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
                data, client_address = self.serverSocket.recvfrom(1024)
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
                    self.handle_quit_conference(conference_id=int(message),client_address=client_address)


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
            print(environ)
                
        @self.sio.event
        def join_room(sid, data): # the sid is the socket id
            room = data.get('room')
            udp_socket = data.get('udpSocket')
            video_socket = data.get('videoSocket')
            audio_socket = data.get('audioSocket')
            screen_socket = data.get('screenSocket')
            self.sio.save_session(sid, {'room': room, 
                                        'udpSocket': udp_socket, 
                                        'videoSocket': video_socket, 
                                        'audioSocket': audio_socket, 
                                        'screenSocket': screen_socket}
                                  )
            
            if room:
                self.sio.enter_room(sid, room)
                print(f"Client {sid} joined room {room}")
                # self.sio.emit('room_joined', {'message': f'Joined room {room}'}, room=sid)
                room_clients = list(self.sio.manager.get_participants("/", room))
                print(f"Number of clients in room {room}: {len(room_clients)}")
                
                # Change the mode of the room according to the number of clients in the room
                if len(room_clients) <= 2:
                    self.room_manager[room] = 0
                elif len(room_clients) > 2:
                    self.room_manager[room] = 1
                    
                self.sio.emit('mode_change',{'mode':self.room_manager[room],'num_clients':len(room_clients)},room=room)
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

        @self.sio.on('text_message')
        async def handle_text_message(sid, data):
            message = data.get('message')
            conference_id = data.get('conference_id')
            if conference_id not in self.conference_servers:
                await self.sio.emit('error', {'message': f'Conference {conference_id} not found.'}, to=sid)
                return

            formatted_message = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {sid}: {message}"
            await self.sio.emit('text_message', {'message': formatted_message}, room=conference_id)
            print(f"Broadcasted message: {formatted_message}")
        
        @self.sio.on('video_frame')
        def handle_video_frame(sid, data):
            """
            Handle incoming video frames and broadcast to all other clients.
            """
            room = data.get("room")
            frame_with_sender = {
                'frame': data['frame'],
                'sender_id': sid  # Use the Socket.IO sid as the sender identifier
            }
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
            
        @self.sio.on('leave_room')
        def handle_leave_room(sid, data):
            room = data.get('room')
            self.sio.leave_room(sid, room)
            print(f"Client {sid} left room {room}")
            room_clients = list(self.sio.manager.get_participants("/", room))
            print(f"Number of clients in room {room}: {len(room_clients)}")
            # Change the mode of the room according to the number of clients in the room
            if len(room_clients) <= 2:
                self.room_manager[room] = 0
            elif len(room_clients) > 2:
                self.room_manager[room] = 1
            
            self.sio.emit(event='mode_change',data={'mode':self.room_manager[room],'num_clients':len(room_clients)},room=room)
            
        @self.sio.on('get_clients')
        def handle_get_clients(sid, data):
            room = data.get('room')
            room_clients = list(self.sio.manager.get_participants("/", room)) # the return value is a list of (socketid,sid)
            print(room_clients)
            # Acquire the ports of each client
            clients_info = []
            for client_sid,_ in room_clients:
                # if client_sid != sid:
                    session_data = self.sio.get_session(client_sid,namespace='/')
                    client_info = {
                        'sid': client_sid,
                        'udp_socket': session_data.get('udpSocket'),
                        'video_socket': session_data.get('videoSocket'),
                        'audio_socket': session_data.get('audioSocket'),
                        'screen_socket': session_data.get('screenSocket')
                    }
                    clients_info.append(client_info)
            
            self.sio.emit(event='clients_list', data=clients_info, to=sid)
            print(f"Client {sid} requested clients list in room {room}")


if __name__ == '__main__':
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT)
    server.start()