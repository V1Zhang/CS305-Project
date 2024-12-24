import io
import socket
import threading
import cv2
from PIL import Image
from aioquic.asyncio import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
import util,config
import pyaudio
import numpy as np
import wave
# from rtp import RTP,Extension,PayloadType
import struct
import queue
from time import time
import RtpPacket
import pydub
import random
import base64
import pyautogui
from flask import Flask, Response, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import socketio as SOCKET

# TODO: 文字传输改为TCP


class ConferenceClient:
    def __init__(self):
        self.is_working = True
        self.server_addr = None
        self.on_meeting = False
        self.conns = None
        self.support_data_types = []
        self.share_data = {}
        self.conference_port = None
        self.conference_audio_port = None
        self.conference_video_port = None
        self.recv_data = None
        self.threads = {}
        self.join_success = threading.Event()
        self.conference_id = None
        # self.quic_config = QuicConfiguration(is_client=True)
        self.Socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.Socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.Socket.bind(('0.0.0.0', 0))
        self.available_conferences = []

        # 前后端通信的端口
        async_mode = "eventlet"
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app,async_mode=async_mode, cors_allowed_origins="*")
        threading.Thread(target=self.run_flask_server, daemon=True).start()
        CORS(self.app)

        # client和server通信的端口
        self.sio = SOCKET.Client(logger=False, engineio_logger=False)
        self.register_socketio_events()
        
        ## video part
        self.cap = None
        self.video_thread = None
        self.video_running = False
        self.video_queue = queue.Queue()
        self.image_path = "Client/off.jpg"
        
        # audio part
        self.P = None
        self.audio_thread = None
        self.audio_running = False
        self.audio_thread_receive=None
        self.audio_queue = None

        
        # screen share
        self.screen_share_thread = None
        self.screen_share_running = False
        self.screen_data = {}
        self.screen_share_client = None
    
        self.audio_stream=None
        self.p_write = pyaudio.PyAudio()
        self.audio_stream_write = self.p_write.open(format=pyaudio.paInt16,  # 16-bit audio format
                            channels=1,              # 单声道
                            rate=44100,              # 采样率
                            output=True,             # 输出模式
                            frames_per_buffer=2048)  # 缓冲区大小
    
    

    def receive_text_message(self):
        while self.is_working:
            try:
                data, server_address = self.Socket.recvfrom(921600)
                # 预解码
                header = data[:5].decode()
                if header == "AUDIO" or header == "VIDEO":
                    port = struct.unpack('>H', data[5:7])[0]
                    payload = data[7:]
                    if header == "AUDIO":
                        self.receive_audio_stream(payload)
                    elif header == "VIDEO":
                        sender_port= data[5:10]
                        payload = data[12:]
                        self.receive_video_stream(payload, sender_port)
                else:
                    header, port, payload = util.decode_message(data)
                    text_output = f"Receive message from port {port}\n."
                if header == "TEXT ":
                    if self.conference_port == None:
                        self.conference_port = port
                    self.socketio.emit('message', {'type': 'TEXT', 'message': payload})
                elif header == "CREAT":
                    port_message = payload.split(' ')
                    self.conference_audio_port = int(port_message[0])
                    self.conference_video_port = int(port_message[1])
                    self.socketio.emit('message', {'type': 'CREAT', 'message': payload})
                elif header == "JOIN ":
                    self.socketio.emit('message', {'type': 'JOIN', 'message': payload})
                    content = payload.split(':')
                    status_code, conference_id = content[0], content[1]
                    if status_code == "OK":
                        if self.conference_port == None:
                            self.conference_port = port
                        self.join_success.set()
                        self.conference_id = conference_id
                        self.update_status(f"On Meeting {conference_id}")
                    else:
                        # messagebox.showwarning("Warning", f"Join conference {conference_id} failed.")
                        break
                    self.join_conference(conference_id)
                elif header == "QUIT ":
                    self.socketio.emit('message', {'type': 'QUIT', 'message': payload})
                    self.quit_conference()
                    # TODO: 完成取消会议的逻辑，添加按钮，添加会议管理员逻辑
            except Exception as e:
                print(f"Error receiving message: {e}")
                break
 
        
    def run_flask_server(self):
        @self.app.route("/")
        def index():
            return "Welcome to Remote Meeting API!"
            
        @self.app.route('/create_conference', methods=['POST'])
        def create_conference_route():
            try:
                self.create_conference()  # 调用类中的创建会议方法
                return jsonify({
                    "status": "success",
                    "message": f"Conference {self.conference_id} created successfully."
                })
            except Exception as e:
                print(e)
                return jsonify({
                    "status": "error",
                    "message": f"Error creating conference: {str(e)}"
                }), 500
                
        @self.app.route('/join_conference', methods=['POST'])
        def join_conference_route():
            try:
                conference_id = request.get_json().get('conferenceId')
                print(conference_id)
                self.join_conference(conference_id)  # 调用类中的创建会议方法
                return jsonify({
                    "status": "success",
                    "message": f"Joined Conference {self.conference_id} successfully."
                })
            except Exception as e:
                print(e)
                return jsonify({
                    "status": "error",
                    "message": f"Error joining conference: {str(e)}"
                }), 500
                
        @self.app.route('/available_conferences', methods=['GET'])
        def available_conferences_route():
            conferences = self.available_conferences # 示例静态房间号
            return jsonify({"status": "success", "conferences": conferences})
                
        @self.app.route('/quit_conference', methods=['POST'])
        def quit_conference_route():
            """
            Handle a POST request to quit a conference.
            This will process the quit request and clean up resources on the server.
            """
            try:
                isHost = request.get_json().get('isHost')
                if isHost:
                    self.quit_conference()
                else:
                    self.leave_conference()
                return jsonify({
                    "status": "success",
                    "message": f"Left Conference {self.conference_id} successfully."
                })
            
            except Exception as e:
                print(f"Error processing quit request: {e}")
                return jsonify({
                    "status": "error",
                    "message": f"Error leaving conference: {str(e)}"
                }), 500
        
        @self.app.route('/send_message', methods=['POST'])       
        def send_text_message():
            if not self.conference_id:
                return jsonify({
                    "status": "error",
                    "message": "You are not in a conference."
                }), 500
            message = request.get_json().get('message')
            if message:
                try:
                    data = f"TEXT {message}".encode()
                    print(data)
                    self.Socket.sendto(data, (config.SERVER_IP_UDP,config.MAIN_SERVER_PORT_UDP))
                    return jsonify({
                    "status": "success",
                    "message": f"Send TEXT {data}"
                    }), 200
                except Exception as e:
                    return jsonify({
                    "status": "error",
                    "message": f"Error leaving conference: {str(e)}"
                    }), 500
        
        
        @self.app.route('/toggle_video_stream', methods=['POST'])       
        def toggle_video_stream():
            if not self.conference_id:
                return jsonify({
                    "status": "error",
                    "message": f"You are not in a conference."
                    }), 500
            if not self.video_running:
                self.video_running = True
                self.video_thread = threading.Thread(target=self.send_video_stream, daemon=True)
                self.video_thread.start()
                return jsonify({
                    "status": "success",
                    "message": f"video stop"
                    }), 200
            else:
                self.video_running = False
                self.video_thread = threading.Thread(target=self.send_static_img, daemon=True)
                self.video_thread.start()
                return jsonify({
                    "status": "success",
                    "message": f"video start"
                    }), 200
               
        @self.app.route('/toggle_audio_stream', methods=['POST'])
        def toggle_audio_stream():
            if not self.conference_id:
                return jsonify({
                    "status": "error",
                    "message": f"You are not in a conference."
                    }), 500
            action = request.get_json().get('action')
            if self.audio_running is None or self.audio_running==False:
                self.audio_running = True
                self.audio_queue=[]
                self.audio_thread = threading.Thread(target=self.send_audio_stream, daemon=True)
                
                self.audio_thread.start()
                return jsonify({
                    "status": "success",
                    "message": f"audio stop"
                    }), 200
            else:
                self.audio_running = False
                return jsonify({
                    "status": "shut",
                    "message": f"audio start"
                    }), 200
                
        @self.app.route('/toggle_screen_share', methods=['POST'])       
        def toggle_screen_share():
            if not self.conference_id:
                return jsonify({
                    "status": "error",
                    "message": f"You are not in a conference."
                    }), 500
            if not self.screen_share_running:
                self.screen_share_running = True
                self.screen_share_thread = threading.Thread(target=self.send_screen_share, daemon=True)
                self.screen_share_thread.start()
                return jsonify({
                    "status": "success",
                    "message": f"screen share start"
                    }), 200
            else:
                self.screen_share_running = False
                return jsonify({
                    "status": "success",
                    "message": f"screen share stop"
                    }), 200
            
        @self.app.route('/get_room', methods=['GET'])
        def get_room():
            room_id = self.conference_id # 示例静态房间号
            return jsonify({"room_id": room_id})
      
                
            
        # @self.socketio.on('connect')
        # def handle_connect():
        #     print("Client connected")
        @self.socketio.on('connect')
        def handle_connect():
            print('Client connected with SID:', request.sid)  # 打印连接用户的 SID
        
        
        
            
           

    def register_socketio_events(self):


        @self.sio.event
        def connect():
            print("Connected to server")
            print(self.sio.sid)
            self.sio.emit('join_room', { 'room': self.conference_id })
            threading.Thread(target=send_heartbeat, daemon=True).start()  # 启动心跳线程

        def send_heartbeat():
            while self.sio.connected:
                self.sio.emit('heartbeat', {'message': 'ping'})
                time.sleep(10)  # 每 10 秒发送一次心跳

        @self.sio.on('client_info')
        def handle_client_info(data):
            pass
        
        @self.socketio.on('available_conferences')
        def handle_available_conferences(data):
            self.available_conferences = data['conferences']
    
        

        @self.sio.event
        def disconnect(reason=None):
            print(f"Disconnected from server. Reason: {reason}")
            

        @self.sio.on('audio_stream')
        def handle_audio_stream(data):
            """Handle incoming audio stream.""" 
            audio_data = base64.b64decode(data)
            self.audio_stream_write.write(audio_data)
                
            
    def create_conference(self):
        if not self.conference_id:
            conference_id = ''.join(random.choices('0123456789', k=6))
            if conference_id and conference_id.isdigit():
                host_thread = threading.Thread(target=self.receive_text_message, daemon=True)
                host_thread.start()
                self.threads['host'] = host_thread
                text_output = f"Conference id {conference_id} Created."
                self.conference_id = conference_id
                self.host = True
                message = f"CREAT{conference_id}"
                try:
                    data = message.encode()
                    self.Socket.sendto(data, (config.SERVER_IP, config.MAIN_SERVER_PORT))
                    text_output = f"Sent: {message}\n"
                    IP= 'http://'+config.SERVER_IP_LOGIC+ ":" + str(config.MAIN_SERVER_PORT_LOGIC)
                    print(IP) 
                    self.sio.connect(IP)
                    # 加入对应房间
                    # room = str(self.conference_id)  # 动态指定房间号
                    # self.sio.connect(f"{IP}?room={room}")
                except Exception as e:
                    print("Error", f"Error sending message: {e}")
                    
                return jsonify({
                "status": "success",
                "text_output": text_output,
                "conference_id": conference_id
            })
                
        else:
            return jsonify({
            "status": "error",
            "text_output": "You are already in a conference."
        })


    def join_conference(self, conference_id):
        text_output = f"Joined Conference {conference_id}.\n"
        message = f"JOIN {conference_id}"
        try:
            data = message.encode()
            self.Socket.sendto(data,(config.SERVER_IP,config.MAIN_SERVER_PORT))
            text_output = f"Sent: {message}\n"
            self.conference_id=conference_id
            IP= 'http://'+config.SERVER_IP_LOGIC+ ":" + str(config.MAIN_SERVER_PORT_LOGIC)
            # 加入对应房间
            room = str(self.conference_id)  # 动态指定房间号
            self.sio.connect(f"{IP}?room={room}")
        except Exception as e:
            print("Error", f"Error sending message: {e}")
        guest_thread = threading.Thread(target=self.receive_text_message, daemon=True)
        guest_thread.start()
        return jsonify({
                "status": "success",
                "text_output": text_output,
                "conference_id": conference_id
            })

    def quit_conference(self):
        if not self.conference_id:
            print("Warning", "You are not in a conference.")
            return
        message = f"QUIT {self.conference_id}"
        try:
            data = message.encode()
            self.Socket.sendto(data,(config.SERVER_IP,config.MAIN_SERVER_PORT))
            text_output = f"Sent: {message}\n"
        except Exception as e:
            print("Error", f"Error sending message: {e}")
        self.conference_id = None
        self.conference_port = None
        self.join_success.clear()
        text_output = text_output + "Left the conference.\n"
        return jsonify({
                "status": "success",
                "text_output": text_output,
                "conference_id": self.conference_id
            })


    def send_video_stream(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.video_running = True

        while self.video_running:
            _, img = self.cap.read()
            img = cv2.flip(img, 1)

            _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 30])
            video_data = base64.b64encode(buffer).decode('utf-8')
            
            if not self.sio.connected:
                    print("Waiting for reconnection...")
                    continue
            
            # Send video frame via Socket.IO
            # self.sio.emit('video_frame', {'frame': video_data, 'sender_id': self.sio.sid,"room": str(self.conference_id)})
            self.sio.emit('video_frame', {'frame': video_data, 'sender_id': config.SELF_IP,"room": str(self.conference_id)})
        self.cap.release()
        cv2.destroyAllWindows()
        
    def send_static_img(self):
        while not self.video_running:
            img = cv2.imread(self.image_path)
            img = cv2.resize(img, (680, 480))
            _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 30])
            video_data = base64.b64encode(buffer).decode('utf-8')
            
            if not self.sio.connected:
                    print("Waiting for reconnection...")
                    continue
            
            self.sio.emit('video_frame', {'frame': video_data, 'sender_id': config.SELF_IP,"room": str(self.conference_id)})
        self.cap.release()
        cv2.destroyAllWindows()

    def receive_video_stream(self, video_data,client_address):
        """
        Receive video stream from other clients and enqueue it for GUI update.
        """
        # TODO: 标识到底是哪个client
        # TODO: 关闭视频流传输会让画面消失 关闭的时候也发送一条指令
        print("Receive video stream.")
        self.video_queue.put((video_data, client_address))
        
        is_sharing_screen = False


    # def process_video_queue(self):
    #     """
    #     Process video data from the queue and update the GUI.
    #     """
    #     while not self.video_queue.empty():
    #         video_data, client_address = self.video_queue.get()
    #         nparr = np.frombuffer(video_data, np.uint8)
    #         img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    #         if img is not None:
    #             img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    #             img_pil = Image.fromarray(img_rgb)
                
    #             img_io = io.BytesIO()
    #             img_pil.save(img_io, 'JPEG')
    #             img_io.seek(0)
    #             # Base64 encode the video frame for WebSocket transmission
    #             base64_frame = io.BytesIO(img_io.read()).getvalue()
    #             print('send')
    #             # Emit the video stream to front-end
    #             self.socketio.emit('video-stream', {
    #                 'clientAddress': self.socketio.sid,
    #                 'videoFrame': base64_frame.decode('latin1')  # Send binary data as string
    #             })



    def send_audio_stream(self):
        self.p = pyaudio.PyAudio()
        self.audio_stream = self.p.open(format=pyaudio.paInt16,  # 16-bit audio format
                            channels=1,              # 单声道
                            rate=44100,              # 采样率
                            input=True,              # 输入模式
                            frames_per_buffer=4096)  # 缓冲区大小
        while self.audio_running:
            # 从麦克风读取音频数据
            audio_data = self.audio_stream.read(2048)
            encoded_audio = base64.b64encode(audio_data).decode('utf-8')
            # 发送音频数据到服务器
            if not self.sio.connected:
                    print("Waiting for reconnection...")
                    continue
            self.sio.emit('audio_stream', {'data':encoded_audio,"room": str(self.conference_id)})

        self.audio_stream.stop_stream()
        self.audio_stream.close()
        self.p.terminate()


    def send_screen_share(self):
        """Capture the screen and send it periodically to the server."""
        while self.screen_share_running:
            # 捕捉屏幕
            screenshot = pyautogui.screenshot()
            screenshot = screenshot.resize((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
            # screenshot.save('screenshot.png') 
           
            # 将屏幕截图转换为字节流
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            # 压缩图像并编码为 base64
            screen_data = base64.b64encode(img_byte_arr).decode('utf-8')
            # 使用 socket.io 发送屏幕截图
            self.sio.emit('screen_frame', {'frame': screen_data, 'sender_id': self.sio.sid,"room": str(self.conference_id)})

            
    def receive_screen_share(self, screen_data, client_address):
        """Receive and display a shared screen image."""
        print(screen_data)
        self.screen_data = screen_data
        self.screen_share_client = client_address
        
    def process_screen_share(self):  
        # print(self.screen_data)
        if self.screen_data:
            
            frame_data = base64.b64decode(self.screen_data['frame'])
            base64_frame = io.BytesIO(frame_data).getvalue()

            if not self.sio.connected:
                    print("Waiting for reconnection...")
            else:
                self.socketio.emit('video-stream', {
                        'clientAddress': self.socketio.sid,
                        'videoFrame': base64_frame.decode('latin1')  # Send binary data as string
                    })

   
            
            
    def start(self):
        self.socketio.run(self.app, host="0.0.0.0", port=7777, debug=False)
        # self.app.run(host="0.0.0.0", port=7777, debug=True)
    
    def on_closing(self):
        self.is_working = False
        self.video_running = False
        self.audio_running = False
        self.screen_running = False
        for thread in self.threads.values():
            thread.join(timeout=1)
        if self.P:
            self.P.terminate()
        self.Socket.close()

if __name__ == '__main__':
    client1 = ConferenceClient()
    print(client1.Socket.getsockname())
    client1.start()

