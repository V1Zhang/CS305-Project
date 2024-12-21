<template>
  <div>
    <v-header/>
    <div id="page_container" style="text-align: center;">
      <div class="container">
        <transition name="scroll">
          <div class="sentence" v-if="currentSentence">{{ currentSentence }}</div>
        </transition>
      </div>
      <div class="sport">
        <img src="../assets/icon/sport.svg" alt="sport icon" class="sport-icon">
        Start Training Now!
      </div>
      <div class="action-list" v-if="!videoVisible">
        <div v-for="action in actions" style="display: flex; justify-content: space-between; align-items: center;">
          <div class="action-item"
               :key="action.id"
               :data-id="action.id"
               @mouseenter="selectAction(action)"
               @mouseleave="deselectAction(action)"
               @click="handleActionClick(action)"
               :style="{ backgroundColor: action === selectedAction ? ' #191970' : '#FFFFFF', color: action === selectedAction ? 'white' : '#000000'}">
            <button class="action-image">
              <img :src="action.imageUrl" :alt="action.name">
            </button>
            <div class="action-text">{{ action.name }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import img1 from '../assets/img/foream_plank.png'
import img5 from '../assets/img/left_right_bridge.png'
import {useMainStore} from '../store/data.ts';
import vHeader from '../components/header.vue';

const mainStore = useMainStore()
export default {
  components: {
    vHeader
  },
  data() {
    return {
      sentences: [
        "Good morning! Exercise makes the day better!",
        "Keep pushing, you're doing great!",
        "Stay active, stay healthy!",
        "Fitness is not a destination, it's a way of life.",
        "Believe in yourself and all that you are.",
        "A little progress each day adds up to big results.",
        "Stay positive, work hard, make it happen.",
        "Your body can stand almost anything. It’s your mind that you have to convince.",
        "Don't limit your challenges, challenge your limits.",
        "Strive for progress, not perfection."
      ],
      currentSentence: '',
      index: 0,
      selectedAction: null,
      selectedActionVideo: null,
      actions: [
        {
          id: 1,
          name: ' Create Meeting',
          imageUrl: img1
        },
        {
          id: 2,
          name: ' Join Meeting',
          imageUrl: img5
        },
      ]
    }
  },
  created() {
    this.updateSentence();
    setInterval(this.updateSentence, 5000);
  },
  methods: {
    getVideoSrcById(videoId) {
      const videoMap = {
        'Foream Plank': video1,
        'Sumo Glute Bridge': video2
      };
      return videoMap[videoId] || '';
    },
    showVideo() {
      this.videoVisible = true;
      this.$nextTick(() => {
        this.$refs.video.play();
      });
    },
    closeVideo() {
      this.videoVisible = false;
      this.$refs.video.pause();
    },
    updateSentence() {
      this.currentSentence = this.sentences[this.index];
      this.index = (this.index + 1) % this.sentences.length;
    },
    selectAction(action) {
      this.selectedAction = action;
    },
    deselectAction(action) {
      if (this.selectedAction === action) {
        this.selectedAction = null;
      }
    },
    selectActionVideo(action) {
      this.selectedActionVideo = action;
    },
    deselectActionVideo(action) {
      if (this.selectedActionVideo === action) {
        this.selectedActionVideo = null;
      }
    },
    async handleActionClick(action) {
      console.log(`Selected action: ${action.name}`);
      mainStore.update({text: action.id, name: action.name});
      await new Promise(resolve => setTimeout(resolve, 500));
      this.$router.push('/interaction');
    },
    handleActionVideoClick(action) {
      console.log(`Selected action: ${action.name}`);
      this.videoSrc = this.getVideoSrcById(action.name);
      this.showVideo();
    }
  }
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

.sport {
  font-size: 27px;
  display: flex;
  align-items: center;
  margin: 10px 0;
  font-weight: bolder;
}

.sport-icon {
  margin-right: 10px;
  height: 52px;
  width: 52px;
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

.action-image {
  width: 50px;
  height: 50px;
  margin-left: 10px;
  margin-right: 20px;
}

.action-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
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
</style>