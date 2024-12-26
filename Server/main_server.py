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
        
        self.sio = socketio.Server(async_mode='eventlet',cors_allowed_origins=["http://localhost:5173","http://localhost:5174","http://localhost:5175",
                                                                               "http://127.0.0.1:7000","https://admin.socket.io"],
                                   ping_interval=10, ping_timeout=20 ,

                                   max_http_buffer_size=10000000,
                                   logger=False,  # 禁用 Flask-SocketIO 的日志输出
                                   engineio_logger=False  # 禁用 Engine.IO 的日志输出
                                   )
        self.sio.instrument(auth={
            'username':'admin',
            'password':'123456'
        })

        self.app = socketio.Middleware(self.sio)
        self.register_socketio_events()
        eventlet.wsgi.server(eventlet.listen(('', 7000)), self.app)
        
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
            print(environ)
                
        @self.sio.event
        def join_room(sid, data): # the sid is the socket id
            room = data.get('room')

            udp_socket = data.get('udpSocket')
            video_socket = data.get('videoSocket')
            audio_socket = data.get('audioSocket')
            screen_socket = data.get('screenSocket')
            if udp_socket:
                print(f"Client {sid} joined room {room} with UDP socket {udp_socket}")
                self.sio.save_session(sid, {'room': room, 
                                            'udpSocket': udp_socket, 
                                            'videoSocket': video_socket, 
                                            'audioSocket': audio_socket, 
                                            'screenSocket': screen_socket}
                                    )
            
            if room:
                if room not in self.conference_servers:
                    self.conference_servers[room] = {
                        "clients_info": []  # Initialize an empty list
                    }
                    self.conference_servers[room]["clients_info"].append(sid)
                    conferences = [conference_id for conference_id, server in self.conference_servers.items()]
                    print(conferences)
                self.sio.enter_room(sid, room)
                print(f"Client {sid} joined room {room}")
                
                # Checkt if the client is a valid p2p client
                
                room_clients = list(self.sio.manager.get_participants("/", room))
                cnt = 0
                for client_sid, _ in room_clients:
                    if self.sio.get_session(client_sid,namespace='/'):
                        cnt += 1
                print(f"Number of clients in room {room}: {cnt}")
                
                # Change the mode of the room according to the number of clients in the room
                if cnt <= 0:
                    self.room_manager[room] = 0
                elif cnt > 0:
                    self.room_manager[room] = 1
                    
                self.sio.emit('mode_change',{'mode':self.room_manager[room],'num_clients':cnt},room=room)
            else:
                print('error')

        @self.sio.event
        def disconnect(sid):
            rooms = self.sio.rooms(sid=sid)
            for room in rooms:
                self.sio.leave_room(sid=sid,room=room)
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
        def handle_join_conference(sid, data):
            conference_id = data.get('conference_id')
            if conference_id not in self.conference_servers:
                self.conference_servers[conference_id].clients_info.append(sid)
                conferences = [conference_id for conference_id, server in self.conference_servers.items()]
                print(conferences)
                self.sio.emit('create_conference', {'conference_id': conference_id}, to=sid)
                return

            self.conference_servers[conference_id].clients_info.append(sid)
            print(f"Client {sid} joined conference {conference_id}.")
            self.sio.emit('joined_conference', {'conference_id': conference_id}, to=sid)

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
            message = message.decode('utf-8')
            print(message)
            room = data.get('room')
            user = data.get('sender_id')
            # if room not in self.conference_servers:
            #     print('error')
            #     self.sio.emit('error', {'message': f'Conference {room} not found.'}, to=sid)
            #     return

            formatted_message = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {user}: {message}"
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
            # print(data['sender_id'])
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
            audio = data.get("data")
            frame_with_sender = {
                'audio': audio,
            }
            self.sio.emit('audio_stream', frame_with_sender,room=room)
            
        @self.sio.on('heartbeat')  # 自定义心跳事件
        def heartbeat(sid, data):
            print(f'Heartbeat from {sid}: {data}')
            self.sio.emit('heartbeat_response', {'status': 'ok'}, to=sid)
        
        @self.sio.on('leave_room') # a client leaves the room
        def handle_leave_room(sid, data):
            room = data.get('room')
            self.sio.leave_room(sid, room)
            print(f"Client {sid} left room {room}")
            room_clients = list(self.sio.manager.get_participants("/", room))
            cnt = 0
            for client_sid, _ in room_clients:
                if self.sio.get_session(client_sid,namespace='/'):
                    cnt += 1
            print(f"Number of clients in room {room}: {cnt}")
            # Change the mode of the room according to the number of clients in the room
            if cnt <= 2:
                self.room_manager[room] = 0
            elif cnt > 2:
                self.room_manager[room] = 1
            
            self.sio.emit(event='mode_change',data={'mode':self.room_manager[room],'num_clients':cnt},room=room)
            
        @self.sio.on('cancel_room')
        def handle_cancel_room(sid, data):
            room = data.get('room')
            self.sio.emit('room_cancelled',data={'room': room}, room=room)
            print(f"Room {room} is closed.")
            
        @self.sio.on('room_cancelled_ack') # count the number of acks
        def handle_room_cancelled_ack(sid, data):
            room = data.get('room')
            del self.conference_servers[room]
            self.sio.close_room(room)
            
            
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
                    if session_data:
                        client_info = {
                            'sid': client_sid,
                            'udp_socket': session_data.get('udpSocket'),
                            'video_socket': session_data.get('videoSocket'),
                            'audio_socket': session_data.get('audioSocket'),
                            'screen_socket': session_data.get('screenSocket')
                        }
                        clients_info.append(client_info)
            
            self.sio.emit(event='clients_list', data=clients_info)
            print(f"Client {sid} requested clients list in room {room}")


if __name__ == '__main__':
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT)
    # server.start()