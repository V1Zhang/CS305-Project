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
    
        
        print('The server is ready to receive')

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

        # @self.sio.on('create_conference')
        # async def handle_create_conference(sid, data):
        #     conference_id = data.get('conference_id')
        #     if conference_id in self.conference_servers:
        #         await self.sio.emit('error', {'message': f'Conference {conference_id} already exists.'}, to=sid)
        #         return
            
        #     conference_server = ConferenceServer(conference_id=conference_id)
        #     self.conference_servers[conference_id] = conference_server
        #     conference_server.clients_info.append(sid)

        #     # Run ConferenceServer in a separate thread
        #     conference_thread = threading.Thread(target=self.run_conference_server, args=(conference_server,))
        #     conference_thread.start()
        #     self.threads[conference_id] = conference_thread

        #     print(f"Conference {conference_id} created by {sid}.")
        #     await self.sio.emit('conference_created', {'conference_id': conference_id}, to=sid)

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
        def handle_text_message(sid, data):
            message = data.get('message')
            print(message)
            room = data.get('room')
            # if room not in self.conference_servers:
            #     print('error')
            #     self.sio.emit('error', {'message': f'Conference {room} not found.'}, to=sid)
            #     return

            formatted_message = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {sid}: {message}"
            self.sio.emit('text_message', {'message': formatted_message}, room=room)
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
    # server.start()