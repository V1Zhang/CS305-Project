import asyncio
import socket
import time
import threading
import cv2
import numpy as np


class ConferenceServer:
    def __init__(self):
        # async server
        self.conference_id = None  # conference_id for distinguishing different conferences
        self.conf_serve_ports = None
        self.data_serve_ports = {}
        self.data_types = ['screen', 'camera', 'audio']  # example data types in a video conference
        self.clients_info = None
        self.client_conns = None
        self.mode = 'Client-Server'  # or 'P2P' if you want to support peer-to-peer conference mode
        self.running = True

    async def handle_data(self, reader, writer, data_type):
        """Handle incoming data stream from clients"""
        pass

    async def handle_client(self, reader, writer):
        """Handle in-meeting requests or messages from clients"""
        pass

    async def log(self):
        while self.running:
            print('Server status log...')
            await asyncio.sleep(5)

    async def cancel_conference(self):
        """Cancel conference request: disconnect all connections and cancel the conference"""
        pass

    async def start(self):
        """Start the conference server and necessary running tasks"""
        while self.running:
            await asyncio.sleep(1)


class MainServer:
    def __init__(self, server_ip, main_port):
        self.server_ip = server_ip
        self.server_port = main_port
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.serverSocket.bind((server_ip, main_port))
        print('The server is ready to receive')

        self.clients = []

    async def request_handler(self, reader, writer):
        """Handle out-meeting requests from clients"""
        pass

    def broadcast_message(self, message, sender_address):
        """Broadcast messages to all connected clients except the sender"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        formatted_message = f"[{timestamp}] {sender_address}: {message}"
        broadcast_data = f"TEXT {formatted_message}".encode()  # Protocol header

        print(f"Broadcasting message: {formatted_message}")
        for client in self.clients:
            try:
                self.serverSocket.sendto(broadcast_data, client)
            except Exception as e:
                print(f"Error sending message to {client}: {e}")

    async def handle_client(self):
        """Receive and handle client requests in a loop."""
        while True:
            try:
                data, client_address = self.serverSocket.recvfrom(921600)
                if not data:
                    continue
                header, payload = data[:5].decode(), data[5:]  # Protocol header
                print(header)

                if client_address not in self.clients:
                    self.clients.append(client_address)

                if header == "TEXT ":
                    message = payload.decode()
                    self.broadcast_message(message, client_address)

                elif header == "VIDEO":  # Decode received image data
                    frame_data = np.frombuffer(payload, dtype='uint8')
                    img = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)

                    if img is not None:
                        # Display "server" text on the image
                        cv2.putText(img, "server", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                        cv2.imshow('server', img)

                elif header == "AUDIO":
                    print("Audio data received (not yet implemented).")

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            except Exception as e:
                print(f"Error: {e}")
                break

        self.serverSocket.close()
        cv2.destroyAllWindows()

    def start(self):
        """Start MainServer and handle client connections."""
        loop = asyncio.get_event_loop()
        try:
            loop.create_task(self.handle_client())  # Handle client requests asynchronously
            loop.run_forever()  # Keep the server running
        except KeyboardInterrupt:
            print("Server interrupted, shutting down...")
            loop.close()  # Close the event loop gracefully
            self.serverSocket.close()  # Close the socket
            cv2.destroyAllWindows()


if __name__ == '__main__':
    server = MainServer('127.0.0.1', 7000)
    server.start()
