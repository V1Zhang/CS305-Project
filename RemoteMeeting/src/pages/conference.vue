<template>
  <div>
    <v-header />
    <div class="conference-header">
      <span>Conference ID: {{ conferenceId }}</span>
    </div>
    <div class="container">
      <!-- 左侧按钮和视频 -->
      <div id="video-button-container">
        <div class="buttons-container">
          <button @click="toggleVideoStream" class="action-button warning">
            <span class="action-icon">🎥</span> {{ videoButtonText }}
          </button>
          <button @click="toggleAudioStream" class="action-button warning">
            <span class="action-icon">🔊</span> {{ audioButtonText }}
          </button>
          <button @click="toggleScreenShare" class="action-button warning">
            <span class="action-icon">📺</span> {{ screenShareButtonText }}
          </button>
          <button @click="quitConference" class="action-button warning">
            <span class="action-icon">🚪</span> {{ isHost ? 'End Meeting' : 'Quit Meeting' }}
          </button>
        </div>
        <!-- 视频显示区域 -->
        <div class="video-container">
          <div class="camera-container">
            <div v-for="stream in videoStreams" :key="stream.clientAddress" class="video-window">
              <div class="video-header">
                <span>{{ stream.clientAddress }}</span>
              </div>
                <img :src="'data:image/jpeg;base64,' + stream.videoFrame" />
            </div>
          </div>
          <!-- 屏幕共享区 -->
          <div class="screen-share-container">
            <div class="video-header">Screen Share</div>

            <img id="player" style="width:904px;height:576px"/>


          </div>
        </div>
      </div>

      <!-- 右侧聊天区域 -->
      <div class="chat-container">
        <div class="text-output" ref="textOutput">
          <textarea v-model="textOutput" readonly class="output-textarea"></textarea>
        </div>
        <div class="message-input">
          <input type="text" v-model="messageInput" @keyup.enter="sendMessage" placeholder="Type a message..."
            class="input-textarea" />
          <button @click="sendMessage" class="action-button warning">
            <span class="action-icon">✉️</span> Send Message
          </button>
        </div>
      </div>
    </div>

  </div>
</template>
  
  <script>
  import {useMainStore} from '../store/data';
  import vHeader from '../components/header.vue';
  import axios from 'axios';
  import io from 'socket.io-client';

  export default {
    components: {
      vHeader,
    },
    data() {
      return {        
        API_URL: 'http://127.0.0.1:7777',
        IP_URL: 'http://10.32.25.161:7000',
        socket: null,
        store: useMainStore(),
        conferenceId: "",  
        isHost: true,
        videoButtonText: "Start Video Stream", 
        audioButtonText: "Start Audio Stream", 
        screenShareButtonText: "Start Screen Share",
        audioContext: null, // Web Audio API AudioContext
        audioSource: null, // Web Audio API AudioBufferSourceNode
        textOutput: "",        // 显示接收到的消息
        messageInput: "",      // 用户输入的消息
        videoStreams: [],
        screenShareStream: null, // 存储屏幕共享流
        videoStreamStatus: false,
      }
    },
    created() {
      this.socket = io(this.IP_URL);
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      this.socket.on('connect', async () => {
      console.log('Connected to server');
        this.isHost = this.store.text === 1;
        try {
          // 调用 Flask API 获取房间号
          const response = await axios.get(this.API_URL + '/get_room');
          const roomId = response.data.room_id;; // 提取房间号
          this.conferenceId = roomId;
          // 使用房间号加入房间
          this.socket.emit('join_room', { room: roomId });           
            
          console.log(`Joined room: ${roomId}`);
        } catch (error) {
          console.error('Error fetching room ID:', error);
        }

        this.videoStreamUrl = this.API_URL + 'get_video';
      });

    this.socket.on('disconnect', () => {
      console.log('Disconnected to server');
    });
    this.socket.on('text_message', (data) => {
      console.log('Received message:');
      this.handleIncomingMessage(data);
    });

    this.socket.on('video_frame', (data) => {
      // console.log('Video stream')
      this.handleIncomingVideoStream(data);
    });


      this.socket.on('audio_stream', (data) => {
        console.log('audio stream')
        this.handleIncomingAudioStream(data);
      });

    this.socket.on('screen_frame', (data) => {
      this.handleIncomingScreenShare(data);
    });

      this.socket.on('room_cancelled', (data) => {
        this.$router.push('/mode')
      });

    },


  mounted() {
    // 在页面加载后自动调用 toggleVideoStream
    // this.toggleVideoStream();
    },

  beforeDestroy() {
    // 断开 WebSocket 连接
    if (this.socket) {
      this.socket.disconnect();
    }
  },
  methods: {
    handleIncomingMessage(data) {
      this.textOutput += `Text: ${data.message}\n`;
      this.$nextTick(() => {
        const outputElement = this.$refs.textOutput; // 确保绑定了 ref="textOutput"
        if (outputElement) {
          outputElement.scrollTop = outputElement.scrollHeight;
        }
      });
    },

    handleIncomingVideoStream(data) {
      const { frame: videoFrame, sender_id: clientAddress } = data; // 确保字段名称与后端一致
      // console.log('Received video frame data:', data);
      // console.log("sender_id (clientAddress):", clientAddress);


          // 查找是否已有该客户端的视频窗口
          const existingStream = this.videoStreams.find(
            (stream) => stream.clientAddress === clientAddress
          );
          
          if (existingStream) {
            // 如果已存在该客户端的视频流，更新视频帧
            existingStream.videoFrame = videoFrame;
          } else {
            // 如果该客户端的视频流不存在，新增视频流
            this.videoStreams.push({
              clientAddress,
              videoFrame
            });
          }
        },


        handleIncomingAudioStream(data) {
          const { audio: encodedAudio } = data; // Extract Base64-encoded PCM data
          if (!encodedAudio) {
            console.error("No audio buffer received.");
            return;
          }

          // Decode Base64 audio data into raw PCM
          const binaryString = atob(encodedAudio);
          const len = binaryString.length;
          const pcmArray = new Int16Array(len / 2); // 16-bit PCM data
          for (let i = 0; i < len; i += 2) {
            pcmArray[i / 2] = (binaryString.charCodeAt(i + 1) << 8) | binaryString.charCodeAt(i); // Little-endian
          }

          // Create an AudioBuffer from PCM data
          const audioBuffer = this.audioContext.createBuffer(
            1, // Mono
            pcmArray.length, // Number of samples
            44100 // Sample rate (must match sender)
          );
          const bufferChannel = audioBuffer.getChannelData(0); // Get buffer for the first channel
          for (let i = 0; i < pcmArray.length; i++) {
            bufferChannel[i] = pcmArray[i] / 32768; // Normalize 16-bit PCM to [-1, 1]
          }

          // Manage audio playback by batching audio frames
          if (!this.audioQueue) {
            this.audioQueue = [];
          }

          // Store the decoded audio buffer in the queue
          this.audioQueue.push(audioBuffer);

          // Play audio in batches
          if (!this.isPlaying && this.audioQueue.length > 0) {
            this.isPlaying = true;
            this.playBufferedAudio();
          }
        },

playBufferedAudio() {
  if (this.audioQueue.length === 0) {
    this.isPlaying = false;
    return;
  }

  const audioBuffer = this.audioQueue.shift(); // Get the next audio buffer from the queue

  // Create and play the audio source
  const source = this.audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(this.audioContext.destination);
  source.onended = () => {
    // Once the current buffer has finished playing, check if there are more
    if (this.audioQueue.length > 0) {
      this.playBufferedAudio();
    } else {
      this.isPlaying = false;
    }
  };

  // Start playback
  source.start(0);
},


    handleIncomingScreenShare(data) {
      const { frame: videoFrame, sender_id: clientAddress } = data;
      const existingStream = this.videoStreams.find(
        (stream) => stream.clientAddress === clientAddress
      );
      const player = document.getElementById('player');
      player.src = 'data:image/jpeg;base64,' + videoFrame;
    },


        async quitConference() {
            try {
                const response = await axios.post(this.API_URL + '/quit_conference', {
                  isHost: this.isHost, // 示例数据
                });

        if (response.status === 200) {
          console.log("Conference quited: ", response.data);
        } else {
          console.error("Failed to quit conference", response.data);
        }
      } catch (error) {
        console.error("Error creating conference:", error);
      }
      await new Promise(resolve => setTimeout(resolve, 500));
      this.$router.push('/mode');
    },


        async toggleVideoStream() {
            try {
                const response = await axios.post(this.API_URL + '/toggle_video_stream', {
                  action: this.videoStreamStatus ? "stop" : "start"  // 根据当前状态发送启动或停止请求
                });

                if (response.data.status === 'success') {
                  this.videoStreamStatus = !this.videoStreamStatus;
                  this.videoButtonText = this.videoStreamStatus ? "Stop Video Stream" : "Start Video Stream";
                  if (this.videoStreamStatus) {
                    // 如果视频流启动，设定视频流的地址
                    this.videoStreamUrl = this.API_URL + '/get_video';
                  }else {
                    // console.error('Error toggling video stream:', response.data.message);
                  }
                } else {
                console.error('Error toggling video stream:', response.data.message);
                }
            } catch (error) {
                console.error("Error toggling video stream:", error);
            }
        },

        async toggleAudioStream() {
            try {
                const response = await axios.post(this.API_URL + '/toggle_audio_stream', {
                action: this.AudioStreamStatus ? "stop" : "start"  // 根据当前状态发送启动或停止请求
                });

        if (response.data.status === 'success') {
          this.audioButtonText = "Stop Audio Stream"

        } else {
          this.audioButtonText = "Start Audio Stream"
        }
      } catch (error) {
        // 捕获并打印错误信息
        console.error("Error toggling audio stream:", error);
      }
    },

        async toggleScreenShare() {
            try {
                const response = await axios.post(this.API_URL + '/toggle_screen_share', {
                action: this.ScreenShareStatus ? "stop" : "start"  
                });

        if (response.data.status === 'success') {
          this.ScreenShareStatus = !this.ScreenShareStatus;
          this.screenShareButtonText = this.ScreenShareStatus ? "Stop Screen Share" : "Start Screen Share";
          if (this.ScreenShareStatus) {
            console.log('Screen Shrare started successfully.');
          } else {
            // this.screenShareStream = null;
            // const player = document.getElementById('player');
            // if (player) {
            //   player.src = '';  // 清空屏幕共享区域的显示内容
            // }
            console.log('Screen Shrare stopped successfully.');
          }
        } else {
          // 如果后端返回错误，打印错误信息
          console.error('Error toggling screen shrare:', response.data.message);
        }
      } catch (error) {
        // 捕获并打印错误信息
        console.error("Error toggling screen shrare:", error);
      }
    },

    async sendMessage() {
      if (!this.messageInput.trim()) {
        return;  // 不发送空消息
      }

          try {
            // 假设向后端发送消息的接口是 `send_message`
            const response = await axios.post(this.API_URL + '/send_message', {
              message: this.messageInput,
            });

            if (response.data.status === 'success') {
              // this.textOutput += `You: ${this.messageInput}\n`;  // 添加到输出区域
              this.messageInput = "";  // 清空输入框
            } else {
              console.error('Error sending message:', response.data.message);
            }
          } catch (error) {
            console.error("Error sending message:", error);
          }
        },
    }
  }


</script>

<style scoped>
.container {
  display: flex;
  /* 使用 Flexbox 让子元素并排显示 */
  justify-content: space-between;
  /* 在主轴方向上分配空间 */
  align-items: flex-start;
  /* 垂直方向对齐 */
  padding: 20px;
  margin-top: 0;
  gap: 20px;
  /* 为左右容器之间增加间距 */
}

.conference-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
  background-color: #f0f0f0;
  border-radius: 10px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
  /* 给下方内容添加一些间距 */
}

.conference-header span {
  font-size: 16px;
  font-weight: bold;
}

#video-button-container {
  display: flex;
  flex-direction: column;
  /* 垂直排列按钮 */
  justify-content: flex-start;
  align-items: center;
  width: 70%;
  background-color: #f5f5f5;
  /* 背景色 */
  border-radius: 10px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
}

.buttons-container {
  display: flex;
  flex-direction: row;
  gap: 20px;
  /* 按钮之间的间距 */
  margin-top: 20px;
  /* 按钮容器顶部间距 */
}

.action-button {
  display: flex;
  align-items: center;
  background-color: #000000;
  border-radius: 37px;
  border: 3px solid #FFFFFF;
  height: 52px;
  padding: 9px 17px;
  max-width: 450px;
  color: white;
  font-size: 12px;
  font-weight: bold;
  cursor: pointer;
  transition: transform 0.2s;
}

.action-button:hover {
  transform: scale(1.2);
}

.action-icon {
  margin-right: 10px;
  height: 20px;
  width: 20px;
}

/* 视频显示区域 */
.video-container {
  display: flex;
  flex-direction: column;
  /* 上下排列视频窗口和屏幕共享区域 */
  gap: 10px;
  /* 设置间距 */
  margin-top: 20px;
}

.video-header {
  font-weight: bold;
  margin-bottom: 10px;
}


.camera-container {
  background-color: #f0f0f0;
  flex-direction: row;
  border-radius: 8px;
  padding: 10px;
  box-shadow: 0 0 15px rgba(0, 0, 0, 0.1);
}

.camera-container img {
  max-width: 25%;
  max-height: 25%;
  object-fit: contain;
}

.screen-share-container {
  background-color: #f0f0f0;
  border-radius: 8px;
  padding: 10px;
  box-shadow: 0 0 15px rgba(0, 0, 0, 0.1);
}

.screen-share-container img {
  width: 100%;
  /* 自适应宽度 */
  max-width: 704px;
  max-height: 576px;
  object-fit: contain;
}



/* 聊天容器 */
#chat-container {
  right: 0;
  top: 20%;
  /* 防止和底部重叠 */
  width: 450px;
  background-color: #f9f9f9;
  border: 1px solid #ddd;
  border-radius: 10px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  display: flex;
  flex-direction: column;
}

.text-output {
  height: 700px;
  padding: 10px;
  background-color: #fff;
  flex: 1;
  border-bottom: 1px solid #ddd;
  overflow-y: scroll;
  font-family: Arial, sans-serif;
  font-size: 14px;
}

.output-textarea {
  width: 100%;
  height: 100%;
  border: none;
  background: transparent;
  color: #333;
  resize: none;
  font-family: Arial, sans-serif;
}

.message-input {
  display: flex;
  align-items: center;
  padding: 10px;
  border-top: 1px solid #ddd;
}

.input-textarea {
  flex: 1;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 5px;
  font-family: Arial, sans-serif;
  font-size: 14px;
}
</style>