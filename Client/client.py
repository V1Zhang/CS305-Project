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

from flask import Flask, Response, request, jsonify
from flask_cors import CORS

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

        # GUI setup
        self.app = Flask(__name__)
        threading.Thread(target=self.run_flask_server, daemon=True).start()
        CORS(self.app)
        
        
        ## video part
        self.cap = None
        self.video_thread = None
        self.video_running = False
        # audio part
        self.P = None
        self.audio_thread = None
        self.audio_running = False

    
    

    def receive_text_message(self):
        while self.is_working:
            try:
                data, server_address = self.Socket.recvfrom(921600)
                # 预解码
                header = data[:5].decode()
                print(data)
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
                    text_output = f"Received: {payload}\n"
                elif header == "CREAT":
                    port_message = payload.split(' ')
                    self.conference_audio_port = int(port_message[0])
                    self.conference_video_port = int(port_message[1])
                    text_output = f"Received: {payload}\n"
                elif header == "JOIN ":
                    text_output = f"Received: {payload}\n"
                    content = payload.split(':')
                    status_code, conference_id = content[0], content[1]
                    if status_code == "OK":
                        if self.conference_port == None:
                            self.conference_port = port
                        self.join_success.set()
                        self.conference_id = conference_id
                        self.update_status(f"On Meeting {conference_id}")
                        text_output = f"Joined Conference {conference_id}.\n"
                    else:
                        # messagebox.showwarning("Warning", f"Join conference {conference_id} failed.")
                        break
                    self.join_conference(conference_id)
                elif header == "QUIT ":
                    text_output = f"Received: {payload}\n"
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
                
        @self.app.route('/quit_conference', methods=['POST'])
        def quit_conference_route():
            """
            Handle a POST request to quit a conference.
            This will process the quit request and clean up resources on the server.
            """
            try:
                self.quit_conference()
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
                    self.Socket.sendto(data, (config.SERVER_IP, self.conference_port))
                    return jsonify({
                    "status": "success",
                    "message": f"Send TEXT {message}"
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
            action = request.get_json().get('action')
            self.video_running = False if action=='start' else True
            if not self.video_running:
                self.video_running = True
                self.video_thread = threading.Thread(target=self.send_video_stream, daemon=True)
                self.video_thread.start()
                return jsonify({
                    "status": "success",
                    "message": f"video start"
                    }), 200
            else:
                self.video_running = False
                return jsonify({
                    "status": "success",
                    "message": f"video stop"
                    }), 200
               
        @self.app.route('/toggle_audio_stream', methods=['POST'])
        def toggle_audio_stream():
            if not self.conference_id:
                return jsonify({
                    "status": "error",
                    "message": f"You are not in a conference."
                    }), 500
            action = request.get_json().get('action')
            self.audio_running = False if action=='start' else True
            if not self.audio_running:
                self.audio_running = True
                self.audio_thread = threading.Thread(target=self.send_audio_stream, daemon=True)
                self.audio_thread.start()
                return jsonify({
                    "status": "success",
                    "message": f"audio start"
                    }), 200
            else:
                self.audio_running = False
                return jsonify({
                    "status": "success",
                    "message": f"audio stop"
                    }), 200


        @self.app.route("/get_video", methods=["GET"])
        def get_video():
            """
            用于流式返回视频帧。
            """
            def generate():
                while True:
                    if self.last_frame:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + self.last_frame + b'\r\n\r\n')
                    else:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + b'\r\n\r\n')
            return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")
        

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
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        addr = (config.SERVER_IP, self.conference_video_port)


        while self.video_running:
            _, img = self.cap.read()
            img = cv2.flip(img, 1)
           
            if img is None:
                return
            _, send_data = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 30])
            video_data = send_data.tobytes()
            self.Socket.sendto(video_data, addr)
            # Convert OpenCV image to PIL image for Tkinter
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
            # img_tk = ImageTk.PhotoImage(img_pil)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # When video stops, release the capture and clear the video label
        self.cap.release()

    def receive_video_stream(self, video_data,client_address):
        """
        Receive video stream from other clients and enqueue it for GUI update.
        """
        # TODO: 标识到底是哪个client
        # TODO: 关闭视频流传输会让画面消失 关闭的时候也发送一条指令
        print("Receive video stream.")
        self.video_queue.put((video_data, client_address))

    def process_video_queue(self):
        """
        Process video data from the queue and update the GUI.
        """
        while not self.video_queue.empty():
            video_data, client_address = self.video_queue.get()
            nparr = np.frombuffer(video_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(img_rgb)
                
                img_io = io.BytesIO()
                img_pil.save(img_io, 'JPEG')
                img_io.seek(0)
                
                self.last_frame = img_io.read()

                
                # # 检查是否已经为该客户端创建了视频标签
                # if client_address not in self.other_video_labels:
                #     # 创建一个新的标签来显示接收到的视频
                #     video_label = tk.Label(self.window)
                #     video_label.pack(side=tk.LEFT, padx=10, pady=10)  # 可以根据需要调整布局
                #     self.other_video_labels[client_address] = video_label

                # # 更新对应客户端的标签
                # self.other_video_labels[client_address].config(image=img_tk)
                # self.other_video_labels[client_address].image = img_tk

        self.root.after(10, self.process_video_queue)

    def receive_audio_stream(self, audio_data):
        """
        Receive audio stream from other clients and play it.
        """
        # TODO: 辨别多个client的音轨
        if not self.P:
            self.P = pyaudio.PyAudio()
            self.audio_stream = self.P.open(format=pyaudio.paInt16,
                                            channels=1,
                                            rate=44100,
                                            output=True,
                                            frames_per_buffer=2048)
        try:
            self.audio_stream.write(audio_data)
        except Exception as e:
            print(f"Error playing audio data: {e}")

    

    def send_audio_stream(self):
        self.P=pyaudio.PyAudio()
        audio_stream = self.P.open(format=pyaudio.paInt16,channels=1,rate=44100,input=True,frames_per_buffer=2048)
        # output_stream = self.P.open(format=pyaudio.paInt16,channels=1, rate=44100,output=True,frames_per_buffer=2048)
        addr = (config.SERVER_IP, self.conference_audio_port)

        while self.audio_running:
            audio_data = audio_stream.read(2048)      # 读出声卡缓冲区的音频数据
            print(len(audio_data))
            # output_stream.write(audio_data)  # Write audio to speakers
            # audio_data = b"AUDIO" + audio_data
            self.Socket.sendto(audio_data, addr)

        audio_stream.stop_stream()
        audio_stream.close()
        # 终止PyAudio对象，释放占用的系统资源
        self.P.terminate()


   
            
            
    def start(self):
        self.app.run(host="0.0.0.0", port=7777, debug=True)
    
    def on_closing(self):
        self.is_working = False
        self.video_running = False
        self.audio_running = False
        for thread in self.threads.values():
            thread.join(timeout=1)
        if self.P:
            self.P.terminate()
        self.Socket.close()

if __name__ == '__main__':
    client1 = ConferenceClient()
    print(client1.Socket.getsockname())
    client1.start()

