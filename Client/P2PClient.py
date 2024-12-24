import socket
import threading
import struct
import time
import queue
import numpy as np
import cv2

from util import encode_message, decode_message
from config import SELF_IP

class P2PClient:
    def __init__(self, audio_stream):
        
        self.udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udpSocket.bind((SELF_IP, 0))
        self.udp_port = self.udpSocket.getsockname()[1]

        
        self.audio_rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.audio_rtpSocket.bind((SELF_IP, 0))
        self.audio_rtp_port = self.audio_rtpSocket.getsockname()[1]

        
        self.video_rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.video_rtpSocket.bind((SELF_IP, 0))
        self.video_rtp_port = self.video_rtpSocket.getsockname()[1]

        
        self.screen_rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.screen_rtpSocket.bind((SELF_IP, 0))
        self.screen_rtp_port = self.screen_rtpSocket.getsockname()[1]

        self.clients_info = []  # [{'udp_socket':(ip,port), 'audio_socket':..., 'video_socket':..., ...}, ...]

        
        self.audio_stream = audio_stream

        self.audio_rtpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 921600)
        self.video_rtpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 921600)
        self.screen_rtpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 921600)

        self.audio_buffer = queue.Queue()

        self.is_running = False
        self.threads = []
        
    def start(self):
        self.is_running = True

        
        t_text = threading.Thread(target=self._receive_text_loop, daemon=True)
        t_text.start()
        self.threads.append(t_text)

        
        t_audio = threading.Thread(target=self._receive_audio_loop, daemon=True)
        t_audio.start()
        self.threads.append(t_audio)

        
        t_video = threading.Thread(target=self._receive_video_loop, daemon=True)
        t_video.start()
        self.threads.append(t_video)

        
        t_screen = threading.Thread(target=self._receive_screen_loop, daemon=True)
        t_screen.start()
        self.threads.append(t_screen)

        
        t_playback = threading.Thread(target=self._playback_audio_loop, daemon=True)
        t_playback.start()
        self.threads.append(t_playback)
        
        print(self.threads)

    def close(self):
        self.is_running = False
        self.udpSocket.close()
        self.audio_rtpSocket.close()
        self.video_rtpSocket.close()
        self.screen_rtpSocket.close()
        for t in self.threads:
            t.join(timeout=1)
        print("P2PClient closed.")


    def send_text_message(self, message):
        
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        sender_addr = self.udpSocket.getsockname()
        formatted = f"[{timestamp}] {sender_addr}: {message}"
        data = encode_message("TEXT ", self.udp_port, formatted)
        for client in self.clients_info:
            addr = (client.get('udp_socket')[0],client.get('udp_socket')[1])  # (ip, port)
            if not addr:
                continue
            try:
                self.udpSocket.sendto(data, addr)
            except Exception as e:
                print(f"Failed to send TEXT to {addr}: {e}")

    def forward_rtp_data(self, raw_data, data_type):
        
        for client in self.clients_info:
            if data_type == 'audio':
                dst = (client.get('audio_socket')[0],client.get('audio_socket')[1])
                header = b"AUDIO"
                port_bytes = struct.pack('>H', self.audio_rtp_port)
            elif data_type == 'video':
                dst = (client.get('video_socket')[0],client.get('video_socket')[1])
                header = b"VIDEO"
                port_bytes = struct.pack('>H', self.video_rtp_port)
            elif data_type == 'screen':
                dst = (client.get('screen_socket')[0],client.get('screen_socket')[1])
                header = b"SHARE"
                port_bytes = struct.pack('>H', self.screen_rtp_port)
            else:
                continue

            if dst:
                packet = header + port_bytes + raw_data
                try:
                    if data_type == 'audio':
                        self.audio_rtpSocket.sendto(packet, dst)
                    elif data_type == 'video':
                        self.video_rtpSocket.sendto(packet, dst)
                    elif data_type == 'screen':
                        self.screen_rtpSocket.sendto(packet, dst)
                except Exception as e:
                    print(f"Failed to send {data_type} to {dst}: {e}")

    def _receive_text_loop(self):
        while self.is_running:
            try:
                data, addr = self.udpSocket.recvfrom(65535)
                header, sender_port, payload = decode_message(data)
                if header == "TEXT ":
                    print(f"[Text] from {addr}: {payload}")
                    # TODO: Front end display
                else:
                    print(f"[Unknown TEXT header={header}] from {addr}")
            except OSError:
                break
            except Exception as e:
                print(f"Text receive error: {e}")
                break

    def _receive_audio_loop(self):
        while self.is_running:
            try:
                data, addr = self.audio_rtpSocket.recvfrom(65535)
                header = data[:5].decode(errors="ignore")
                port = struct.unpack('>H', data[5:7])[0]
                payload = data[7:]

                if header == "AUDIO":
                    self.handle_audio_data(payload)
                else:
                    pass
            except OSError:
                break
            except Exception as e:
                print(f"Audio receive error: {e}")
                break

    def _receive_video_loop(self):
        while self.is_running:
            try:
                data, addr = self.video_rtpSocket.recvfrom(65535)
                header = data[:5].decode(errors="ignore")
                port = struct.unpack('>H', data[5:7])[0]
                payload = data[7:]
                if header == "VIDEO":
                    self.handle_video_frame(payload)
                    #TODO: front end display
                    pass
                else:
                    pass
            except OSError:
                break
            except Exception as e:
                print(f"Video receive error: {e}")
                break

    def _receive_screen_loop(self):
        while self.is_running:
            try:
                data, addr = self.screen_rtpSocket.recvfrom(65535)
                header = data[:5].decode(errors="ignore")
                port = struct.unpack('>H', data[5:7])[0]
                payload = data[7:]
                if header == "SHARE":
                    # TODO: handle screen data
                    pass
                else:
                    pass
            except OSError:
                break
            except Exception as e:
                print(f"Screen receive error: {e}")
                break


    def handle_audio_data(self, data):
        self.audio_buffer.put(data)

    def handle_video_frame(self, data):
        frame_data = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
        if img is not None:
            cv2.imshow("P2P Video", img)
            cv2.waitKey(1)


    def _playback_audio_loop(self):
        while self.is_running:
            try:
                raw_data = self.audio_buffer.get(timeout=1)
                self.audio_stream.write(raw_data)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Audio playback error: {e}")
                break
