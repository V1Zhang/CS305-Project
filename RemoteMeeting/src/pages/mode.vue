<template>
  <div>
    <v-header/>
    <div id="page_container" style="text-align: center;">

      <!-- 显示可加入的会议 -->
      <div v-if="availableConferences.length > 0" class="conference-list">
        <h2>Available Conferences</h2>
        <ul>
          <li v-for="conference in availableConferences" :key="conference">
            {{ conference }}
          </li>
        </ul>
      </div>
      <div v-else>
        <p>No available conferences at the moment.</p>
      </div>

      <div class="action-list">
        <div v-for="action in actions" :key="action.id" style="display: flex; justify-content: space-between; align-items: center;">
          <div class="action-item"
               :key="action.id"
               :data-id="action.id"
               @mouseenter="selectAction(action)"
               @mouseleave="deselectAction(action)"
               @click="handleActionClick(action)"
               :style="{ backgroundColor: action === selectedAction ? ' #191970' : '#FFFFFF', color: action === selectedAction ? 'white' : '#000000'}">
            <div class="action-text">{{ action.name }}</div>
          </div>
        </div>
      </div>
    </div>
    
    <div v-if="showJoinModal" class="modal">
      <div class="modal-content">
        <h2>Join Meeting</h2>
        <input v-model="conferenceId" type="text" placeholder="Enter conference ID" />
        <button @click="joinConference">Join</button>
        <button @click="closeModal">Cancel</button>
      </div>
    </div>
  </div>
</template>

<script>
import vHeader from '../components/header.vue';
import axios from 'axios';
import {useMainStore} from '../store/data.ts';
import io from 'socket.io-client';

const mainStore = useMainStore()
export default {
  components: {
    vHeader
  },
  data() {
    return {
      API_URL: 'http://127.0.0.1:7778',
      IP_URL: 'http://10.32.68.67:7000',
      socket: null,
      index: 0,
      selectedAction: null,
      actions: [
        {
          id: 1,
          name: ' Create Meeting',
        },
        {
          id: 2,
          name: ' Join Meeting',
        }
      ],
      showJoinModal: false, // Controls the modal visibility
      conferenceId: "", // Holds the conference ID input by the user
      availableConferences: [], // List of available conferences
    }
  },
  created() {
    this.socket = io(this.IP_URL);
    this.socket.on('connect', () => {
      console.log('Connected to server');
      this.socket.emit('get_available_conferences');
    });
    this.socket.on('available_conferences', (data) => {
        console.log(data)
        this.fetchAvailableConferences(data); // Fetch available conferences on load
      });
  },
  methods: {
    selectAction(action) {
      this.selectedAction = action;
    },
    deselectAction(action) {
      if (this.selectedAction === action) {
        this.selectedAction = null;
      }
    },
    async handleActionClick(action) {
      mainStore.update({text: action.id, name: action.name});
      if (action.id === 1) {  //  "Create Meeting"
      try {
            // 发送 POST 请求到后端的 create_conference 方法
            const response = await axios.post(this.API_URL + '/create_conference', {
            // 如果需要传递参数，可以在这里添加
            userId: "user123", // 示例数据
            });

            if (response.status === 200) {
            console.log("Conference Created: ", response.data);
            // 可以做一些状态更新，比如更新界面上的状态
            } else {
            console.error("Failed to create conference", response.data);
            }
        } catch (error) {
            console.error("Error creating conference:", error);
        }
        await new Promise(resolve => setTimeout(resolve, 500));
        this.$router.push('/conference');


      } else if (action.id === 2) {  //  "Join Meeting"
      this.showJoinModal = true; // Show the modal to input conference ID
      }
    },

    async fetchAvailableConferences(data) {
      const {status: status, conferences: conferences} = data;
      if (status === 'success') {
        this.availableConferences = conferences;
        console.log('Available conferences:', this.availableConferences);
      } else {
          console.error('Failed to fetch conferences', data);
      }
    },

    async joinConference() {
      // 检查用户输入的会议ID是否为空
      if (!this.conferenceId) {
        alert("Please enter a valid conference ID.");
        return;
      }

      try {
        const response = await axios.post(this.API_URL + '/join_conference', {
          userId: "user123", // 示例数据
          conferenceId: this.conferenceId // 用户输入的会议ID
        });

        if (response.status === 200) {
          console.log("Joined Conference: ", response.data);
          // 更新UI（例如：加入成功后显示会议详情或状态）
          this.showJoinModal = false; // 成功后关闭模态框
          await new Promise(resolve => setTimeout(resolve, 500));
          this.$router.push('/conference');
        } else {
          console.error("Failed to join conference", response.data);
          alert("Failed to join conference. Please try again.");
        }
      } catch (error) {
        console.error("Error joining conference:", error);
        alert("Error joining conference. Please try again.");
      }
    },

    closeModal() {
      this.showJoinModal = false; // 关闭模态框
      this.conferenceId = ""; // 清空输入框
    }
  },
  
}
</script>

<style scoped>
#page_container {
  background: url("../assets/img/bg.png") center; /* 增加背景图 */
  background-size: 100% 100%; /* 设置背景的大小 */
  background-repeat: no-repeat; /* 将背景设置为不重复显示 */
  height: 100vh; /* 设置容器高度为视口高度 */
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  color: white;
}

.container {
  margin-top: -12%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sentence {
  font-size: 29px;
  display: flex;
  align-items: center;
}

.action-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
}

.action-item {
  width: 290px;
  border: 3px solid #FFFFFF; /* 设置按钮的边界粗细和颜色 */
  margin-top: 17px; /* 设置合适的上部外框的宽度 */
  justify-content: center;
  color: #FFFFFF;
  line-height: 30px;
  border-radius: 30px; /* 将按钮的左右边框设置为圆弧 */
  cursor: pointer;
  display: flex;
  align-items: center; /* 垂直居中 */
  padding: 10px;
  transition: background-color 0.3s, color 0.3s;
}

.action-item:hover {
  transform: scale(1.2);
}

.action-video-item {
  width: 52px;
  border: 3px solid #FFFFFF; /* 设置按钮的边界粗细和颜色 */
  margin-top: 17px; /* 设置合适的上部外框的宽度 */
  margin-left: 20px;
  text-align: center;
  color: #FFFFFF;
  line-height: 30px;
  border-radius: 30px; /* 将按钮的左右边框设置为圆弧 */
  cursor: pointer;
  display: flex;
  align-items: center; /* 垂直居中 */
  padding: 10px;
  transition: background-color 0.3s, color 0.3s;
}

.action-video-item:hover {
  transform: scale(1.2);
}




.action-video {
  border-radius: 22px;
  background-color: white;
  width: 50px;
  height: 50px;
  margin-left: 1px;
  cursor: pointer;
  border: none;
}

.action-video img {
  width: 100%;
  object-fit: cover;
}

.action-text {
  font-size: 20px;
  font-weight: bold;
}

.video-container {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: -72px;
}

.video-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
}

video {
  width: 720px;
  height: 480px;
  background-color: black;
}

.close-button {
  margin-top: 10px;
  border: none;
  cursor: pointer;
  border-radius: 22px;
  background-color: white;
  width: 50px;
  height: 50px;
}

.close-button img {
  margin-top: 2px;
  width: 100%;
  object-fit: cover;
}

.close-button:hover {
  background-color: #00a152;
  transform: scale(1.5);
}


.modal {
  position: fixed;
  top: -280px;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content button {
  width: 100%;
  padding: 12px 20px;
  background: black;
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 16px;
  cursor: pointer;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);  /* 按钮的阴影 */
  transition: background-color 0.3s ease, transform 0.3s ease, box-shadow 0.3s ease;
  margin-bottom: 10px; 
}

.modal-content {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0px 2px 10px rgba(0, 0, 0, 0.2);
  width: 300px;
}

input {
  width: 100%;
  padding: 8px;
  margin: 10px 0;
  border: 1px solid #ccc;
  border-radius: 4px;
}


.conference-list {
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 600px;
  margin: 20px auto;
}

.conference-list h2 {
  text-align: center;
  color: #333;
}
.conference-list li {
  text-align: center;
  color: #333;
}

.conference-list ul {
  list-style-type: none;
  padding: 0;
}

.conference-item {
  display: flex;
  justify-content: space-between;
  padding: 10px;
  margin: 8px 0;
  background-color: #ffffff;
  border: 1px solid #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.conference-item:hover {
  background-color: #f1f1f1;
}

.no-conference-message {
  text-align: center;
  color: #888;
  font-size: 18px;
}
</style>