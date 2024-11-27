import asyncio
from util import *
import socket
import time
import threading
import struct
import config


class ConferenceServer:
    # 客户与会议服务器之间的通信协议应该基于连接，需要多个端口
    def __init__(self,conference_id):
        # async server
        self.conference_id = conference_id  # conference_id for distinguish difference conference
        # 绑定端口
        self.udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udpSocket.bind(('0.0.0.0',0))
        self.udp_port = self.udpSocket.getsockname()[1]

        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtpSocket.bind(('0.0.0.0',0))
        self.rtp_port = self.rtpSocket.getsockname()[1]

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


    def start(self):
        # 暂时还是用UDP作为传输层协议
        '''
        start the ConferenceServer and necessary running tasks to handle clients in this conference
        '''
        print(f"Conference {self.conference_id} server is ready to receive and the udp port is {self.udp_port}")
        # loop.create_task(self.log())
        while True:
            try:
                data, client_address = self.udpSocket.recvfrom(1024)
                if not data:
                    continue
                header, payload = data[:5].decode(), data[5:]
                print(header)
                if header == "TEXT ":
                    message = payload.decode()
                    self.broadcast_message(message,client_address)
            except Exception as e:
                print(f"Error: {e}")
                break

        





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
        conference_thread = threading.Thread(target=conference_server.start)
        conference_thread.start()
        self.threads[conference_id] = conference_thread
        


        

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
                print(header)
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
                    ##
                    print("Audio data received (not yet implemented).")
                elif header == "CREAT":
                    message = payload.decode()
                    print(f"Create conference {message} request received.")
                    self.handle_create_conference(conference_id=int(message),conference_host_address=client_address)

                    reply = f"You have been assigned to conference {message}"
                    print(self.conference_servers[int(message)].udp_port)
                    self.serverSocket.sendto(encode_message("TEXT ",self.conference_servers[int(message)].udp_port,reply), client_address)
                elif header == "JOIN ":
                    message = payload.decode()
                    print(f"Join conference {message} request received.")
                    flag = self.handle_join_conference(conference_id=int(message))
                    if flag:
                        reply = "OK"
                        self.serverSocket.sendto(encode_message("JOIN ", self.server_port, reply), client_address)
                        self.conference_servers[int(message)].clients_info.append(client_address)
                        self.conference_servers[int(message)].broadcast_info(f"{client_address} has joined the conference.",BROADCAST_JOIN)
                    else:
                        reply = f"NK"
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
