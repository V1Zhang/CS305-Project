import av
import numpy as np
import cv2

# 创建一个输出容器（.mp4 文件）
output_file = 'output_h264.mp4'
container = av.open(output_file, mode='w')

# 创建一个视频流，指定 H.264 编码
stream = container.add_stream('h264', rate=30)  # H.264 编码，帧率为 30
stream.width = 640  # 视频宽度
stream.height = 480  # 视频高度
stream.pix_fmt = 'yuv420p'  # 使用 YUV 420 色彩空间（H.264 常用的颜色格式）

# 创建一个视频捕获对象，读取摄像头（你也可以使用其他视频文件作为输入）
cap = cv2.VideoCapture(0)  # 这里使用默认摄像头（ID 0）

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 水平翻转图像（如果是左右颠倒）
    frame = cv2.flip(frame, 1)  # 水平翻转，1 表示左右翻转

    # 将帧从 BGR 转换为 RGB（OpenCV 默认是 BGR，PyAV 需要 RGB）
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 创建 PyAV 的视频帧
    video_frame = av.VideoFrame.from_ndarray(frame_rgb, format='rgb24')

    # 编码视频帧
    for packet in stream.encode(video_frame):
        container.mux(packet)

    # 显示视频帧（如果需要显示）
    cv2.imshow('Video', frame)

    # 按 'q' 键退出循环
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 在视频结束后，添加最后的编码帧（Flush）
for packet in stream.encode():
    container.mux(packet)

# 释放资源
cap.release()
cv2.destroyAllWindows()
container.close()
