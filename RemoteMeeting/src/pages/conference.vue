<template>
  <div>
    <v-header />
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
          <button @click="quitConference" class="action-button warning">
            <span class="action-icon">🚪</span> Quit Conference
          </button>
        </div>
        <div class="video-container">
          <v-video />
        </div>
      </div>

      <!-- 右侧聊天区域 -->
      <div class="chat-container">
        <div class="text-output">
          <textarea v-model="textOutput" readonly class="output-textarea"></textarea>
        </div>
        <div class="message-input">
          <input
            type="text"
            v-model="messageInput"
            @keyup.enter="sendMessage"
            placeholder="Type a message..."
            class="input-textarea"
          />
          <button @click="sendMessage" class="action-button warning">
            <span class="action-icon">✉️</span> Send Message
          </button>
        </div>
      </div>
    </div>

  </div>
</template>
  
  <script>
  import vHeader from '../components/header.vue';
  import vVideo from '../components/video.vue';
  import axios from 'axios';
  

  export default {
    components: {
      vHeader,
      vVideo
    },
    data() {
      return {
        modelVideoUrl: "https://cn-hk-eq-01-10.bilivideo.com/upgcxcode/71/12/1158901271/1158901271-1-192.mp4?e=ig8euxZM2rNcNbRV7WdVhwdlhWdBhwdVhoNvNC8BqJIzNbfq9rVEuxTEnE8L5F6VnEsSTx0vkX8fqJeYTj_lta53NCM=&uipk=5&nbs=1&deadline=1721127940&gen=playurlv2&os=bcache&oi=729892153&trid=00001f4fded7121e43358d7ef7ce1f315b37T&mid=3546712159291839&platform=html5&og=cos&upsig=61932c241c510493aae8565e4a2732ea&uparams=e,uipk,nbs,deadline,gen,os,oi,trid,mid,platform,og&cdnid=68704&bvc=vod&nettype=0&bw=105459&orderid=0,1&buvid=&build=0&mobi_app=&f=T_0_0&logo=80000000",
        videoPopUrl: '', // 初始化视频地址为空
       
        videoButtonText: "Start Video Stream", 
        audioButtonText: "Start Audio Stream", 
        textOutput: "",        // 显示接收到的消息
        messageInput: "",      // 用户输入的消息
      }
    },
    created() {
     
    },
    beforeDestroy() {
      clearInterval(this.interval);
    },
    methods: {
        async quitConference() {
            try {
                const response = await axios.post('http://127.0.0.1:7777/quit_conference', {
                // 如果需要传递参数，可以在这里添加
                userId: "user123", // 示例数据
                });

                if (response.status === 200) {
                console.log("Conference Created: ", response.data);
                } else {
                console.error("Failed to create conference", response.data);
                }
            } catch (error) {
                console.error("Error creating conference:", error);
            }
            await new Promise(resolve => setTimeout(resolve, 500));
            this.$router.push('/mode');
        },


        async toggleVideoStream() {
            try {
                const response = await axios.post('http://127.0.0.1:7777/toggle_video_stream', {
                action: this.videoStreamStatus ? "stop" : "start"  // 根据当前状态发送启动或停止请求
                });

                if (response.data.status === 'success') {
                this.videoStreamStatus = !this.videoStreamStatus;
                this.videoButtonText = this.videoStreamStatus ? "Stop Video Stream" : "Start Video Stream";
                if (this.videoStreamStatus) {
                    // 如果视频流启动，设定视频流的地址
                    this.videoStreamUrl = 'http://127.0.0.1:7777/get_video';
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
                const response = await axios.post('http://127.0.0.1:7777/toggle_audio_stream', {
                action: this.AudioStreamStatus ? "stop" : "start"  // 根据当前状态发送启动或停止请求
                });

                if (response.data.status === 'success') {
                    this.audioStreamStatus = !this.audioStreamStatus;
                    this.audioButtonText = this.audioStreamStatus ? "Stop Audio Stream" : "Start Audio Stream";
                    if (this.audioStreamStatus) {
                        console.log('Audio stream started successfully.');
                    } else {
                        console.log('Audio stream stopped successfully.');
                    }
                } else {
                // 如果后端返回错误，打印错误信息
                console.error('Error toggling audio stream:', response.data.message);
                }
            } catch (error) {
                // 捕获并打印错误信息
                console.error("Error toggling audio stream:", error);
            }
        },

        async sendMessage() {
          if (!this.messageInput.trim()) {
            return;  // 不发送空消息
          }

          try {
            // 假设向后端发送消息的接口是 `send_message`
            const response = await axios.post('http://127.0.0.1:7777/send_message', {
              message: this.messageInput,
            });

            if (response.data.status === 'success') {
              this.textOutput += `You: ${this.messageInput}\n`;  // 添加到输出区域
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
   
  #page_container {
    background: url("../assets/img/bg.png") center;
    background-size: 100% 100%;
    background-repeat: no-repeat;
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    color: white;
    font-size: 19px;
    font-weight: bold;
  }
  
  .container {
  display: flex;  /* 使用 Flexbox 让子元素并排显示 */
  justify-content: space-between;  /* 在主轴方向上分配空间 */
  align-items: flex-start;  /* 垂直方向对齐 */
  padding: 20px;
  margin-top: 0;
  gap: 20px;  /* 为左右容器之间增加间距 */
}

#video-button-container {
  display: flex;
  flex-direction: column;  /* 垂直排列按钮 */
  justify-content: flex-start;
  align-items: center;
  width: 40%;  /* 控制视频按钮区域的宽度 */
  background-color: #f5f5f5;  /* 背景色 */
  padding: 10px;
  border-radius: 10px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
}

.buttons-container {
  display: flex;
  flex-direction: column;
  gap: 20px;  /* 按钮之间的间距 */
  margin-top: 20px;  /* 按钮容器顶部间距 */
}

.action-button {
  display: flex;
  align-items: center;
  background-color: #000000;
  border-radius: 37px;
  border: 3px solid #FFFFFF;
  height: 52px;
  padding: 9px 17px;
  max-width: 440px;
  color: white;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  transition: transform 0.2s;
}

.action-button:hover {
  transform: scale(1.2);
}

.action-icon {
  margin-right: 10px;
  height: 37px;
  width: 37px;
}

/* 视频显示区域 */
.video-container {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
  width: 720px;
  height: 540px;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 22px;
  margin-bottom: -37px;
}

.video-container img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

/* 聊天容器 */
#chat-container {
  right: 0;
  top: 20%;  /* 防止和底部重叠 */
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

.send-button {
  padding: 8px 15px;
  border: 1px solid #4CAF50;
  border-radius: 5px;
  background-color: #4CAF50;
  color: white;
  font-size: 14px;
  cursor: pointer;
  margin-left: 10px;
}

.send-button:hover {
  background-color: #45a049;
}

  </style>