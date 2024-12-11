import asyncio
from util import *
import socket
import time
import threading
import struct
import config
import matplotlib.pyplot as plt
from ConferenceServer import ConferenceServer

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
                    # img = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
                    # if img is not None:
                    #     # 在图像上显示“server”字样
                    #     cv2.putText(img, "server", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                    #     cv2.imshow('server', img)
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
    server = MainServer('127.0.0.1', 7000)
    server.start()
