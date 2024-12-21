import socket
import threading
import cv2
import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk  # To convert OpenCV images to Tkinter images
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
import socketio
import base64

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
        self.window = tk.Tk()
        self.window.title("Conference Client")

        self.status_label = tk.Label(self.window, text="Status: Free", font=("Arial", 12))
        self.status_label.pack()

        self.message_entry = tk.Entry(self.window, width=50)
        self.message_entry.pack()

        self.send_button = tk.Button(self.window, text="Send Message", command=self.send_text_message)
        self.send_button.pack()

        self.text_output = tk.Text(self.window, height=15, width=50)
        self.text_output.pack()

        self.video_button = tk.Button(self.window, text="Start Video Stream", command=self.toggle_video_stream)
        self.video_button.pack()

        self.audio_button = tk.Button(self.window, text="Start Audio Stream", command=self.toggle_audio_stream)
        self.audio_button.pack()

        self.create_button = tk.Button(self.window, text="Create Conference", command=self.create_conference)
        self.create_button.pack()

        self.join_button = tk.Button(self.window, text="Join Conference", command=self.join_conference_gui)
        self.join_button.pack()

        self.quit_button = tk.Button(self.window, text="Quit Conference", command=self.quit_conference_gui)
        self.quit_button.pack()

        self.video_label = tk.Label(self.window)
        self.video_label.pack()

        ## video part
        self.cap = None
        self.video_thread = None
        self.video_running = False
        # audio part
        self.P = None
        self.audio_thread = None
        self.audio_running = False

        # For displaying other users' videos
        self.other_video_labels = {}
        self.video_queue = queue.Queue()
        self.root = self.window  # Tkinter 主窗口引用
        self.root.after(10, self.process_video_queue)
        self.seqnum = 0 # use to indicate the frame number
        self.image_path = "Client/image.jpg"

        # 使用socketio
        self.sio = socketio.Client()
        self.register_socketio_events()
        # Connect to the Socket.IO server
        
        
        


    def update_status(self, status):
        self.status_label.config(text=f"Status: {status}")
    
    def send_text_message(self):
        if not self.conference_id:
            messagebox.showwarning("Warning", "You are not in a conference.")
            return
        message = self.message_entry.get().strip()
        if message:
            try:
                data = f"TEXT {message}".encode()
                self.Socket.sendto(data, (config.SERVER_IP, self.conference_port))
                self.text_output.insert(tk.END, f"Sent: {message}\n")
                self.message_entry.delete(0, tk.END)
            except Exception as e:
                messagebox.showerror("Error", f"Error sending message: {e}")

    def receive_message(self):
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
                    self.text_output.insert(tk.END, f"Receive message from port {port}\n.")
                if header == "TEXT ":
                    if self.conference_port == None:
                        self.conference_port = port
                    self.text_output.insert(tk.END, f"Received: {payload}\n")
                elif header == "CREAT":
                    port_message = payload.split(' ')
                    self.conference_audio_port = int(port_message[0])
                    self.conference_video_port = int(port_message[1])
                    self.text_output.insert(tk.END, f"Received: {payload}\n")
                elif header == "JOIN ":
                    self.text_output.insert(tk.END, f"Received: {payload}\n")
                    content = payload.split(':')
                    status_code, conference_id = content[0], content[1]
                    if status_code == "OK":
                        IP= 'http://'+config.SERVER_IP+ ":" + str(config.MAIN_SERVER_PORT)
                        self.sio.connect(IP)
                        if self.conference_port == None:
                            self.conference_port = port
                        self.join_success.set()
                        self.conference_id = conference_id
                        self.update_status(f"On Meeting {conference_id}")
                        self.text_output.insert(tk.END, f"Joined Conference {conference_id}.\n")
                    else:
                        messagebox.showwarning("Warning", f"Join conference {conference_id} failed.")
                        break
                    self.join_conference(conference_id)
                elif header == "CANCE":
                    self.text_output.insert(tk.END, f"Received: {payload}\n")
                    # self.cancel_conference()
                    # TODO: 完成取消会议的逻辑，添加按钮，添加会议管理员逻辑
                    self.quit_conference()
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def send_video_stream(self):
        # self.cap = cv2.VideoCapture(0)
        # self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        # self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        # addr = (config.SERVER_IP, self.conference_video_port)

        # while self.video_running:
        #     _, img = self.cap.read()
        #     img = cv2.flip(img, 1)
        #     # img = cv2.imread(self.image_path)
        #     if img is None:
        #         print(f"Error: Unable to load image at {self.image_path}")
        #         return
            
        #     _, send_data = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 30])
        #     # _ , send_data = cv2.imencode('.h264', img)
        #     video_data = send_data.tobytes()
        #     self.Socket.sendto(video_data, addr)
        #     self.Socket.sendto(video_data, addr)
        #     self.Socket.sendto(video_data, addr)
        #     # Convert OpenCV image to PIL image for Tkinter
        #     img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        #     img_pil = Image.fromarray(img_rgb)
        #     img_tk = ImageTk.PhotoImage(img_pil)

        #     if cv2.waitKey(1) & 0xFF == ord('q'):
        #         break

        # # When video stops, release the capture and clear the video label
        # self.cap.release()
        # self.video_label.config(image='')  # Clear the image in the Tkinter label

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.video_running = True

        while self.video_running:
            _, img = self.cap.read()
            # img = cv2.imread(self.image_path)
            img = cv2.flip(img, 1)
            _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 30])
            video_data = base64.b64encode(buffer).decode('utf-8')

            # Send video frame via Socket.IO
            self.sio.emit('video_frame', {'frame': video_data, 'sender_id': self.sio.sid})

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
                img_tk = ImageTk.PhotoImage(img_pil)

                # 检查是否已经为该客户端创建了视频标签
                if client_address not in self.other_video_labels:
                    # 创建一个新的标签来显示接收到的视频
                    video_label = tk.Label(self.window)
                    video_label.pack(side=tk.LEFT, padx=10, pady=10)  # 可以根据需要调整布局
                    self.other_video_labels[client_address] = video_label

                # 更新对应客户端的标签
                self.other_video_labels[client_address].config(image=img_tk)
                self.other_video_labels[client_address].image = img_tk

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



    def toggle_video_stream(self):
        if not self.conference_id:
            messagebox.showwarning("Warning", "You are not in a conference.")
            return
        if not self.video_running:
            self.video_running = True
            self.video_thread = threading.Thread(target=self.send_video_stream, daemon=True)
            self.video_thread.start()
            self.video_button.config(text="Stop Video Stream")
        else:
            self.video_running = False
            self.video_button.config(text="Start Video Stream")

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


    
    def toggle_audio_stream(self):
        if not self.conference_id:
            messagebox.showwarning("Warning", "You are not in a conference.")
            return
        if not self.audio_running:
            self.audio_running = True
            self.audio_thread = threading.Thread(target=self.send_audio_stream, daemon=True)
            self.audio_thread.start()
            self.audio_button.config(text="Stop Audio Stream")
        else:
            self.audio_running = False
            self.audio_button.config(text="Start Audio Stream")




    def create_conference(self):
        if not self.conference_id:
            conference_id = simpledialog.askstring("Join Conference", "Enter conference ID:")
            if conference_id and conference_id.isdigit():
                host_thread = threading.Thread(target=self.receive_message, daemon=True)
                host_thread.start()
                self.threads['host'] = host_thread
                self.update_status(f"On Meeting {conference_id}")
                self.text_output.insert(tk.END, f"Conference id {conference_id} Created.\n")
                self.conference_id = conference_id
                self.host = True
                message = f"CREAT{conference_id}"
                try:
                    data = message.encode()
                    self.Socket.sendto(data, (config.SERVER_IP, config.MAIN_SERVER_PORT))
                    self.text_output.insert(tk.END, f"Sent: {message}\n")
                    IP= 'http://'+config.SERVER_IP+ ":" + str(config.MAIN_SERVER_PORT)
                    self.sio.connect(IP)
                except Exception as e:
                    messagebox.showerror("Error", f"Error sending message: {e}")
        else:
            messagebox.showwarning("Warning", "You are already in a conference.")

    def join_conference_gui(self):
        if self.conference_id:
            messagebox.showwarning("Warning", "You are already in a conference.")
            return
        conference_id = simpledialog.askstring("Join Conference", "Enter conference ID:")
        if conference_id and conference_id.isdigit():
            # 后续添加密码验证
            message = f"JOIN {conference_id}"
            try:
                data = message.encode()
                self.Socket.sendto(data,(config.SERVER_IP,config.MAIN_SERVER_PORT))
                self.text_output.insert(tk.END, f"Sent: {message}\n")
            except Exception as e:
                messagebox.showerror("Error", f"Error sending message: {e}")
            guest_thread = threading.Thread(target=self.receive_message, daemon=True)
            guest_thread.start()
        else:
            messagebox.showwarning("Invalid Input", "Conference ID must be a valid number.")

    def join_conference(self, conference_id):
        self.update_status(f"On Meeting - {conference_id}")
        self.text_output.insert(tk.END, f"Joined Conference {conference_id}.\n")

    def quit_conference_gui(self):
        if not self.conference_id:
            messagebox.showwarning("Warning", "You are not in a conference.")
            return
        message = f"QUIT {self.conference_id}"
        try:
            data = message.encode()
            self.Socket.sendto(data,(config.SERVER_IP,config.MAIN_SERVER_PORT))
            self.text_output.insert(tk.END, f"Sent: {message}\n")
        except Exception as e:
            messagebox.showerror("Error", f"Error sending message: {e}")
        self.quit_conference()

    def quit_conference(self):
        self.conference_id = None
        self.conference_port = None
        self.join_success.clear()
        self.update_status("Free")
        self.text_output.insert(tk.END, "Left the conference.\n")

    def cancel_conference(self):
        self.update_status("Free")
        self.text_output.insert(tk.END, "Conference cancelled.\n")

    def start(self):
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()
    
    def on_closing(self):
        self.is_working = False
        self.video_running = False
        self.audio_running = False
        for thread in self.threads.values():
            thread.join(timeout=1)
        if self.P:
            self.P.terminate()
        self.Socket.close()
        self.window.destroy()
    

    ## socketio 的方法
    def register_socketio_events(self):

        @self.sio.event
        def connect():
            print("Connected to server")
        
        @self.sio.on('client_info')
        def handle_client_info(data):
            for client in data:
                if client not in self.other_video_labels:
                    # 创建一个新的标签来显示接收到的视频
                    video_label = tk.Label(self.window)
                    video_label.pack(side=tk.LEFT, padx=10, pady=10)  # 可以根据需要调整布局
                    self.other_video_labels[client] = video_label
        

        @self.sio.event
        def disconnect():
            print("Disconnected from server")

        @self.sio.on('video_frame')
        def handle_video_stream(data):
            """Handle incoming video stream."""
            # Decode video data and process
            frame_data = base64.b64decode(data['frame'])
            nparr = np.frombuffer(frame_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            sender_id = data['sender_id']  # Identify who sent the frame
            if img is not None:
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(img_rgb)
                img_tk = ImageTk.PhotoImage(img_pil)

                # 更新对应客户端的标签
                self.other_video_labels[sender_id].config(image=img_tk)
                self.other_video_labels[sender_id].image = img_tk

            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.video_running = False
                self.sio.disconnect()

    



if __name__ == '__main__':
    client1 = ConferenceClient()
    # print(client1.Socket.getsockname())
    client1.start()
