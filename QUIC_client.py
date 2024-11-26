import asyncio
import cv2
import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk  # To convert OpenCV images to Tkinter images
from aioquic.asyncio import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration


class ConferenceClient:
    def __init__(self, server_host, server_port):
        self.is_working = True
        self.server_host = server_host
        self.server_port = server_port
        self.protocol = None
        self.video_running = False

        # QUIC configuration
        self.quic_config = QuicConfiguration(is_client=True)
        
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

        self.quit_button = tk.Button(self.window, text="Quit Conference", command=self.quit_conference)
        self.quit_button.pack()

        self.video_label = tk.Label(self.window)
        self.video_label.pack()

        self.cap = None

    async def start_quic_connection(self):
        """Start QUIC connection to the server."""
        async with connect(self.server_host, self.server_port, configuration=self.quic_config) as protocol:
            self.protocol = protocol
            self.update_status("Connected")
            self.text_output.insert(tk.END, "Joined the conference.\n")

    async def send_text_message(self):
        """Send a text message over QUIC."""
        message = self.message_entry.get().strip()
        if message and self.protocol:
            data = f"TEXT {message}".encode()
            await self.protocol.send_datagram(data)
            self.text_output.insert(tk.END, f"Sent: {message}\n")
            self.message_entry.delete(0, tk.END)

    async def receive_text_message(self):
        """Receive messages from QUIC."""
        while self.is_working and self.protocol:
            event = await self.protocol.wait_event()
            if event:
                if isinstance(event, QuicConnectionProtocol.DatagramReceived):
                    header, payload = event.data[:5].decode(), event.data[5:]
                    if header == "TEXT ":
                        message = payload.decode()
                        self.text_output.insert(tk.END, f"Received: {message}\n")
                    else:
                        self.text_output.insert(tk.END, "Non-text data received (not handled in this function).\n")

    async def send_video_stream(self):
        """Send video stream over QUIC."""
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        while self.video_running:
            _, img = self.cap.read()
            img = cv2.flip(img, 1)

            _, send_data = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 50])
            video_data = b"VIDEO" + send_data.tobytes()
            if self.protocol:
                await self.protocol.send_datagram(video_data)

            # Convert OpenCV image to PIL image for Tkinter
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
            img_tk = ImageTk.PhotoImage(img_pil)

            # Update the Tkinter label with the new image
            self.video_label.config(image=img_tk)
            self.video_label.image = img_tk

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap.release()
        self.video_label.config(image='')  # Clear the image in the Tkinter label

    def toggle_video_stream(self):
        if not self.video_running:
            self.video_running = True
            asyncio.create_task(self.send_video_stream())
            self.video_button.config(text="Stop Video Stream")
        else:
            self.video_running = False
            self.video_button.config(text="Start Video Stream")

    def quit_conference(self):
        self.is_working = False
        if self.protocol:
            self.protocol.close()
        self.update_status("Free")
        self.text_output.insert(tk.END, "Left the conference.\n")

    def update_status(self, status):
        self.status_label.config(text=f"Status: {status}")

    def start(self):
        asyncio.run(self.run_async())

    async def run_async(self):
        self.window.mainloop()
        await self.start_quic_connection()
        print("Connected to the server.")
        await asyncio.gather(self.receive_text_message())

if __name__ == '__main__':
    client = ConferenceClient(server_host='127.0.0.1', server_port=7000)
    client.start()
