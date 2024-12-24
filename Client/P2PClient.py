import asyncio
from util import *
import socket
import time
import threading
import struct
import config
from queue import Queue, Empty
import base64
import queue

class P2PClient:
    def __init__(self,audio_stream):
        
        # P2P client Socket
        self.udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udpSocket.bind((SELF_IP,0))
        self.udp_port = self.udpSocket.getsockname()[1]

        self.audio_rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.audio_rtpSocket.bind((SELF_IP,0))
        self.audio_rtp_port = self.audio_rtpSocket.getsockname()[1]

        self.video_rtpSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.video_rtpSocket.bind((SELF_IP,0))
        self.video_rtp_port = self.video_rtpSocket.getsockname()[1]
        
        self.screen_rtpSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.screen_rtpSocket.bind((SELF_IP,0))
        self.screen_rtp_port = self.screen_rtpSocket.getsockname()[1]

        '''
        clients_info: list of client socket information:
        [
            {
                'sid': client_sid,
                'udp_socket': client_udp_socket,
                'video_socket': client_video_socket,
                'audio_socket': client_audio_socket,
                'screen_socket': client_screen_socket,
            {
                ...
            },
            
            ...,
        ]
        '''
        self.clients_info = []

        self.audio_stream = audio_stream
        self.audio_rtpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 921600)
        self.audio_rtpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 921600)
        self.video_rtpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 921600)
        self.video_rtpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 921600)
        self.screen_rtpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 921600)
        self.screen_rtpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 921600)
        self.audio_buffer = {} # client_address: AudioSegment
        self.audio_mixer_task = None
        
        self.is_running = False # check if the P2PClient is running
        

    
    def send_text_message(self,message):
        """
        Broadcast text messages to all connected clients except the sender.
        """
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        sender_address = self.udpSocket.getsockname()
        formatted_message = f"[{timestamp}] {sender_address}: {message}"
        broadcast_data = encode_message("TEXT ",self.udp_port,formatted_message)
        print(f"Broadcasting message: {formatted_message}")
        
        client_udp_address = None
        for client in self.clients_info:
            # Fetch the udp socket address of other p2p clients
            client_udp_address = (client.get('udp_socket')[0],client.get('udp_socket')[1])
            # if client_udp_address != sender_address:
            try:
                self.udpSocket.sendto(broadcast_data,client_udp_address)
                print("Message sent.")
            except Exception as e:
                print(f"Error sending message to {client_udp_address}: {e}")

    
    async def start(self):
        '''
        start the P2PClient and necessary running tasks to handle clients in this conference
        '''
        self.is_running = True
        loop = asyncio.get_event_loop()

        self.text_transport, self.text_protocol = await loop.create_datagram_endpoint(
            lambda: TextMessageProtocol(self),
            sock=self.udpSocket
        )
        print(f"Text data is handled on port {self.udp_port}.")
        
        self.audio_transport, self.audio_protocol = await loop.create_datagram_endpoint(
            lambda: RTPProtocol(self, 'audio'),
            sock=self.audio_rtpSocket
        )
        print(f"Audio data is handled on port {self.audio_rtp_port}.")

        
        self.video_transport, self.video_protocol = await loop.create_datagram_endpoint(
            lambda: RTPProtocol(self, 'video'),
            sock=self.video_rtpSocket
        )
        print(f"Video data is handled on port {self.video_rtp_port}.")

        self.screen_transport, self.screen_protocol = await loop.create_datagram_endpoint(
            lambda: RTPProtocol(self, 'screen'),
            sock=self.screen_rtpSocket
        )
        print(f"Screen data is handled on port {self.screen_rtp_port}.")



        try:
            await asyncio.Future()  
        except asyncio.CancelledError:
            pass
        finally:
            self.close()
        
    def send_rtp_to_client(self, data, client, data_type):
        """
        Send data to P2P client
        """

        try:
            if data_type == 'audio':
                transport = self.audio_transport
                header_bytes = "AUDIO".encode()
                port_bytes = struct.pack('>H', self.audio_rtp_port)
                packet = header_bytes + port_bytes + data
            elif data_type == 'video':
                transport = self.video_transport
                header_bytes = "VIDEO".encode()
                port_bytes = struct.pack('>H', self.video_rtp_port)
                packet = header_bytes + port_bytes + data
            elif data_type == 'screen':
                transport = self.screen_transport
                header_bytes = "SHARE".encode()
                port_bytes = struct.pack('>H', self.screen_rtp_port)
                packet = header_bytes + port_bytes + data
            else:
                return       
              
            transport.sendto(packet, client)
        except Exception as e:
                    print(f" Error sending {data_type} to {client}: {e}.")


    def forward_rtp_data(self,data,data_type):
        """
        Forward RTP data to all clients except the sender
        """
        # tasks = []
        client_rtp_address = None
        for client in self.clients_info:
            if data_type == 'audio':
                client_rtp_address = (client.get('audio_socket')[0],client.get('audio_socket')[1])
            elif data_type == 'video':
                client_rtp_address = (client.get('video_socket')[0],client.get('video_socket')[1])
            elif data_type == 'screen':
                client_rtp_address = (client.get('screen_socket')[0],client.get('screen_socket')[1])
                # tasks.append(self.send_rtp_to_client(data, client, data_type, sender_address))
            self.send_rtp_to_client(data, client_rtp_address, data_type)
        # if tasks:
        #     await asyncio.gather(*tasks)

    def handle_video_frame(self, data):
        """
        Decode Video Frame
        """
        frame_data = np.frombuffer(data, dtype='uint8')
        img = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
        if img is not None:
            cv2.putText(img, "server", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            cv2.imshow('server', img)
            cv2.waitKey(1)
            
    def handle_audio_data(self, data):
        """
        Play audio data
        """
        self.audio_stream.write(data)      

    def close(self):
        """
        Shutdown the server
        """
        self.is_running = False
        self.text_transport.close()
        self.audio_transport.close()
        self.video_transport.close()
        self.screen_transport.close()
        self.audio_stream.stop_stream()
        self.audio_stream.close()
        self.P.terminate()
        print(f"P2P client {self.conference_id} is closed.")


        



class TextMessageProtocol(asyncio.DatagramProtocol):
    def __init__(self, server: P2PClient):
        self.server = server

    def connection_made(self, transport):
        self.transport = transport
        print("TextMessageProtocol connection has been established.")

    def datagram_received(self, data, addr):
        try:
            
            header, sender_port, payload = decode_message(data)
            if header == "TEXT ":
                print(f"Received text message from {addr}: {payload}")
                #TODO: Front end logic
                
        except Exception as e:
            print(f"Error occurs when receiving from {addr}: {e}")

    def error_received(self, exc):
        print(f"TextMessageProtocol received an error: {exc}")

    def connection_lost(self, exc):
        print("TextMessageProtocol connection has been lost.")




class RTPProtocol(asyncio.DatagramProtocol):
    def __init__(self, server: P2PClient, data_type: str):
        self.server = server
        self.data_type = data_type

    def connection_made(self, transport):
        self.transport = transport
        print(f"{self.data_type.capitalize()} RTPProtocol has been established.")

    def datagram_received(self, data, addr):
        print(f"received {self.data_type} data from {addr}")
        if self.data_type == 'video':
            #TODO: handle video frame on the front end
            # self.server.handle_video_frame(data)
            pass
        elif self.data_type == 'audio':
            self.server.handle_audio_data(data)
        elif self.data_type == 'screen':
            #TODO: handle screen frame on the front end
            pass
        

    def error_received(self, exc):
        print(f"{self.data_type.capitalize()} error received {exc}")

    def connection_lost(self, exc):
        print(f"{self.data_type.capitalize()} connection is closed.")