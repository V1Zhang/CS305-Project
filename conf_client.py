from util import *
import socket
import threading

class ConferenceClient:
    def __init__(self,):
        # sync client
        self.is_working = True
        self.server_addr = None  # server addr
        self.on_meeting = False  # status
        self.conns = None  # you may need to maintain multiple conns for a single conference
        self.support_data_types = []  # for some types of data
        self.share_data = {}

        self.conference_info = None  # you may need to save and update some conference_info regularly

        self.recv_data = None  # you may need to save received streamd data from other clients in conference

        self.Socket= socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # 创建UDP套接字
        self.Socket.bind(('0.0.0.0', 0))
        
    def send_text_message(self):
        """
        发送文本消息到服务器
        """
        while True:
            message = input("Enter your message (type 'q' to quit): ").strip()
            if message.lower() == 'q':
                break
            try:
                data = f"TEXT {message}".encode()  # 添加协议头
                self.Socket.sendto(data, ('127.0.0.1', 7000))
            except Exception as e:
                print(f"Error sending message: {e}")

                
    def receive_text_message(self):
        """
        接收来自服务器的文本消息
        """
        while True:
            try:
                data, server_address = self.Socket.recvfrom(1024)
                header, payload = data[:5].decode(), data[5:]
                print(header)
                if header == "TEXT ":
                    print(payload.decode())
                else:
                    print("Non-text data received (not handled in this function).")
            except Exception as e:
                print(f"Error receiving message: {e}")
                break
            
    def send_video_stream(self):
        cap = cv2.VideoCapture(0)
        # 设置镜头分辨率，默认是640x480
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        addr = ('127.0.0.1', 7000) 
        while True:
            _, img = cap.read()

            img = cv2.flip(img, 1)

            # 压缩图片
            _, send_data = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 50])
            video_data = b"VIDEO" + send_data.tobytes()
            self.Socket.sendto(video_data,addr)
            # print(f'正在发送数据，大小:{img.size} Byte')

            cv2.putText(img, "client", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            cv2.imshow('client', img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.clientSocket.close()
        cv2.destroyAllWindows()

    def create_conference(self):
        """
        create a conference: send create-conference request to server and obtain necessary data to
        """
        
        threading.Thread(target=self.receive_text_message, daemon=True).start()
        # threading.Thread(target=self.send_video_stream, daemon=True).start()
        self.send_text_message()


    def join_conference(self, conference_id):
        """
        join a conference: send join-conference request with given conference_id, and obtain necessary data to
        """
        pass

    def quit_conference(self):
        """
        quit your on-going conference
        """
        pass

    def cancel_conference(self):
        """
        cancel your on-going conference (when you are the conference manager): ask server to close all clients
        """
        pass

    def keep_share(self, data_type, send_conn, capture_function, compress=None, fps_or_frequency=30):
        '''
        running task: keep sharing (capture and send) certain type of data from server or clients (P2P)
        you can create different functions for sharing various kinds of data
        '''
        pass

    def share_switch(self, data_type):
        '''
        switch for sharing certain type of data (screen, camera, audio, etc.)
        '''
        pass

    def keep_recv(self, recv_conn, data_type, decompress=None):
        '''
        running task: keep receiving certain type of data (save or output)
        you can create other functions for receiving various kinds of data
        '''

    def output_data(self):
        '''
        running task: output received stream data
        '''

    def start_conference(self):
        '''
        init conns when create or join a conference with necessary conference_info
        and
        start necessary running task for conference
        '''

    def close_conference(self):
        '''
        close all conns to servers or other clients and cancel the running tasks
        pay attention to the exception handling
        '''

    def start(self):
        """
        execute functions based on the command line input
        """
        while True:
            if not self.on_meeting:
                status = 'Free'
            else:
                status = f'OnMeeting-{self.conference_id}'

            recognized = True
            cmd_input = input(f'({status}) Please enter a operation (enter "?" to help): ').strip().lower()
            fields = cmd_input.split(maxsplit=1)
            if len(fields) == 1:
                if cmd_input in ('?', '?'):
                    print(HELP)
                elif cmd_input == 'create':
                    self.create_conference()
                    self.send_text_message()
                elif cmd_input == 'quit':
                    self.quit_conference()
                elif cmd_input == 'cancel':
                    self.cancel_conference()
                else:
                    recognized = False
            elif len(fields) == 2:
                if fields[0] == 'join':
                    input_conf_id = fields[1]
                    if input_conf_id.isdigit():
                        self.join_conference(input_conf_id)
                    else:
                        print('[Warn]: Input conference ID must be in digital form')
                elif fields[0] == 'switch':
                    data_type = fields[1]
                    if data_type in self.share_data.keys():
                        self.share_switch(data_type)
                else:
                    recognized = False
            else:
                recognized = False

            if not recognized:
                print(f'[Warn]: Unrecognized cmd_input {cmd_input}')


if __name__ == '__main__':
    client1 = ConferenceClient()
    client1.start()

