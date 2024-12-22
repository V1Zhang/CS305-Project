from flask import Flask
from flask_socketio import SocketIO
import cv2
import base64
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")


def video_stream():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
    addr = (config.SERVER_IP, self.conference_video_port)

    while True:
        success, frame = video.read()
        if not success:
            break  # 视频结束或出错则退出循环

        # 将帧编码为JPEG格式
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue  # 编码失败，则跳过此帧

        # 将编码后的帧转换为Base64字符串
        frame_base64 = base64.b64encode(buffer).decode('utf-8')

        # 发送图像帧数据
        socketio.emit('image_frame', {'image_data': 'data:image/jpeg;base64,' + frame_base64})

        # 控制帧率
        time.sleep(1 / 30)  # 假设视频是30fps


@socketio.on('connect')
def handle_connect():
    print('Client connected')
    socketio.start_background_task(video_stream)


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5002)

