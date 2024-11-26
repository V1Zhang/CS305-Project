import socket
import threading
import cv2
import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk  # To convert OpenCV images to Tkinter images
from aioquic.asyncio import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration

class ConferenceClient:
    def __init__(self):
        self.is_working = True
        self.server_addr = None
        self.on_meeting = False
        self.conns = None
        self.support_data_types = []
        self.share_data = {}
        self.conference_info = None
        self.recv_data = None
        self.is_host = False # if the client is the host of the conference
        self.inconference = False
        # self.quic_config = QuicConfiguration(is_client=True)
        self.Socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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

        self.create_button = tk.Button(self.window, text="Create Conference", command=self.create_conference)
        self.create_button.pack()

        self.join_button = tk.Button(self.window, text="Join Conference", command=self.join_conference_gui)
        self.join_button.pack()

        self.quit_button = tk.Button(self.window, text="Quit Conference", command=self.quit_conference)
        self.quit_button.pack()

        self.video_label = tk.Label(self.window)
        self.video_label.pack()

        self.cap = None
        self.video_thread = None
        self.video_running = False

    def update_status(self, status):
        self.status_label.config(text=f"Status: {status}")
    
    def send_text_message(self):
        message = self.message_entry.get().strip()
        if message:
            try:
                data = f"TEXT {message}".encode()
                self.Socket.sendto(data, ('127.0.0.1', 7000))
                self.text_output.insert(tk.END, f"Sent: {message}\n")
                self.message_entry.delete(0, tk.END)
            except Exception as e:
                messagebox.showerror("Error", f"Error sending message: {e}")

    def receive_text_message(self):
        while self.is_working:
            try:
                data, server_address = self.Socket.recvfrom(1024)
                header, port, payload = self.decode_message(data)
                self.text_output.insert(tk.END, f"Receive message from port {port}\n.")
                if header == "TEXT ":
                    message = payload.decode()
                    self.text_output.insert(tk.END, f"Received: {message}\n")
                else:
                    self.text_output.insert(tk.END, "Non-text data received (not handled in this function).\n")
            except Exception as e:
                print(f"Error receiving message: {e}")
                break
    
    def decode_message(self,data):
        # 报文类型(5 bytes)端口号(2 bytes)数据
        header = data[:5].decode()
        port = int.from_bytes(data[5:7], byteorder='big')
        payload = data[7:]
        return header, port, payload

    def send_video_stream(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        addr = ('127.0.0.1', 7000)
        while self.video_running:
            _, img = self.cap.read()
            img = cv2.flip(img, 1)

            _, send_data = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 50])
            video_data = b"VIDEO" + send_data.tobytes()
            self.Socket.sendto(video_data, addr)

            # Convert OpenCV image to PIL image for Tkinter
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
            img_tk = ImageTk.PhotoImage(img_pil)

            # Update the Tkinter label with the new image
            self.video_label.config(image=img_tk)
            self.video_label.image = img_tk

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # When video stops, release the capture and clear the video label
        self.cap.release()
        self.video_label.config(image='')  # Clear the image in the Tkinter label

    def toggle_video_stream(self):
        if not self.video_running:
            self.video_running = True
            self.video_thread = threading.Thread(target=self.send_video_stream, daemon=True)
            self.video_thread.start()
            self.video_button.config(text="Stop Video Stream")
        else:
            self.video_running = False
            self.video_button.config(text="Start Video Stream")

    def create_conference(self):
        if not self.inconference:
            conference_id = simpledialog.askstring("Join Conference", "Enter conference ID:")
            if conference_id and conference_id.isdigit():
                threading.Thread(target=self.receive_text_message, daemon=True).start()
                self.update_status(f"On Meeting {conference_id}")
                self.text_output.insert(tk.END, f"Conference id {conference_id} Created.\n")
                self.inconference = True
                self.host = True
                message = f"CREAT{conference_id}"
                try:
                    data = message.encode()
                    self.Socket.sendto(data, ('127.0.0.1', 7000))
                    self.text_output.insert(tk.END, f"Sent: {message}\n")
                    self.message_entry.delete(0, tk.END)
                except Exception as e:
                    messagebox.showerror("Error", f"Error sending message: {e}")
        else:
            messagebox.showwarning("Warning", "You are already in a conference.")

    def join_conference_gui(self):
        conference_id = simpledialog.askstring("Join Conference", "Enter conference ID:")
        if conference_id and conference_id.isdigit():
            self.join_conference(conference_id)
        else:
            messagebox.showwarning("Invalid Input", "Conference ID must be a valid number.")

    def join_conference(self, conference_id):
        self.update_status(f"On Meeting - {conference_id}")
        self.text_output.insert(tk.END, f"Joined Conference {conference_id}.\n")

    def quit_conference(self):
        self.update_status("Free")
        self.text_output.insert(tk.END, "Left the conference.\n")

    def cancel_conference(self):
        self.update_status("Free")
        self.text_output.insert(tk.END, "Conference cancelled.\n")

    def start(self):
        self.window.mainloop()

if __name__ == '__main__':
    client1 = ConferenceClient()
    client1.start()
