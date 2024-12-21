<template>
  <div>
    <v-header/>
    <div id="page_container">
      <div class="container">
        <div class="action">
          <img src="../assets/icon/action.svg" alt="action icon" class="action-icon">
          Fitness Action: {{ actionName }}
        </div>
      </div>
      <div id="image-container">
        <v-video/>
      </div>
      <div class="warning">
        <img src="../assets/icon/warning.svg" alt="warning icon" class="warning-icon">
        <p class="custom-text">
          Posture Tips: {{ message }}</p>
      </div>
    </div>
    <!--    <div class="popVideo" id="popVideoBox" @mousemove.stop="mousemove" @mouseleave.stop="mouseleave">-->
    <!--      <div class="open" v-open></div>-->
    <!--      <div class="drag" v-drag>-->
    <!--        <div class="videoPop">-->
    <!--          <div v-show="replaceIcon" class="videoReplay" @click="changeVideoId">替换</div>-->
    <!--          <div class="closeVideo" @click="close"></div>-->
    <!--        </div>-->
    <!--        <vue-aliplayer-v2 class="aliplayerCon" :source="modelVideoUrl"-->
    <!--                          ref="popVideo"-->
    <!--                          :options="options"-->
    <!--                          @snapshoted="snapshoted"/>-->
    <!--      </div>-->
    <!--    </div>-->
  </div>
</template>

<script>
import {useMainStore} from '../store/data';
import vHeader from '../components/header.vue';
import vVideo from '../components/video.vue';

export default {
  directives: {
    // 拖拽
    drag(el) {
      var odiv = document.getElementById("popVideoBox")
      el.onmousedown = function (eve) {
        eve = eve || window.event;
        var clientX = eve.clientX;
        var clientY = eve.clientY;
        var odivX = odiv.offsetLeft;
        var odivY = odiv.offsetTop;
        var odivLeft = clientX - odivX;
        var odivTop = clientY - odivY;
        var clientWidth = document.documentElement.clientWidth;
        var oWidth = odiv.clientWidth;
        var odivRight = clientWidth - oWidth;
        var clientHeight = document.documentElement.clientHeight;
        var oHeight = odiv.clientHeight;
        var odivBottom = clientHeight - oHeight;
        document.onmousemove = function (e) {
          //e.preventDefault();
          var left = e.clientX - odivLeft;
          if (left < 0) {
            left = 0
          }
          if (left > odivRight) {
            left = odivRight
          }
          var Top = e.clientY - odivTop;
          if (Top < 0) {
            Top = 0
          }
          if (Top > odivBottom) {
            Top = odivBottom
          }
          odiv.style.left = left + "px";
          odiv.style.top = Top + "px";
        }
        document.onmouseup = function () {
          document.onmouseup = "";
          document.onmousemove = "";
        }
      }
    },
    // 放大缩小
    open: function (el) {
      //当被绑定的元素插入到 DOM 中时 放大缩小
      el.onmousedown = function (e) {
        //鼠标按下，计算当前元素距离可视区的距离
        var x = e.clientX - el.offsetLeft;
        var y = e.clientY - el.offsetTop;
        document.onmousemove = function (eve) {
          console.log(y)
          console.log(x)
          //设置宽高
          document.getElementById("popVideoBox").style.height = -y + eve.clientY + "px"
          if (document.getElementById("popVideoBox").offsetHeight > document.body.offsetHeight) {
            document.getElementById("popVideoBox").style.height = document.body.offsetHeight + "px"
          } else if (document.getElementById("popVideoBox").offsetHeight < 150) {
            document.getElementById("popVideoBox").style.height = 150 + "px"
          }
          document.getElementById("popVideoBox").style.width = -x + eve.clientX + "px"
          if (document.getElementById("popVideoBox").offsetWidth > document.body.offsetWidth) {
            document.getElementById("popVideoBox").style.width = document.body.offsetWidth + "px"
          } else if (document.getElementById("popVideoBox").offsetWidth < 150) {
            document.getElementById("popVideoBox").style.width = 150 + "px"
          }
        }
        document.onmouseup = function () {
          document.onmousemove = null;
          document.onmouseup = null;
        }
      }
    }
  },
  components: {
    vHeader,
    vVideo
  },
  data() {
    return {
      modelVideoUrl: "https://cn-hk-eq-01-10.bilivideo.com/upgcxcode/71/12/1158901271/1158901271-1-192.mp4?e=ig8euxZM2rNcNbRV7WdVhwdlhWdBhwdVhoNvNC8BqJIzNbfq9rVEuxTEnE8L5F6VnEsSTx0vkX8fqJeYTj_lta53NCM=&uipk=5&nbs=1&deadline=1721127940&gen=playurlv2&os=bcache&oi=729892153&trid=00001f4fded7121e43358d7ef7ce1f315b37T&mid=3546712159291839&platform=html5&og=cos&upsig=61932c241c510493aae8565e4a2732ea&uparams=e,uipk,nbs,deadline,gen,os,oi,trid,mid,platform,og&cdnid=68704&bvc=vod&nettype=0&bw=105459&orderid=0,1&buvid=&build=0&mobi_app=&f=T_0_0&logo=80000000",
      videoPopUrl: '', // 初始化视频地址为空
      options: {},    // 初始化视频播放选项
      replaceIcon: false, // 根据需要初始化替换图标的显示状态
      store: useMainStore(),
      message: 'Welcome!',
      heartRate: 77,
      actionName: "Foream Plank"
    }
  },
  created() {
    this.fetchMessage();
  },
  mounted() {
    this.fetchAction();
    this.generateRandomHeartRate();
    this.interval = setInterval(this.generateRandomHeartRate, 1000);
  },
  beforeDestroy() {
    clearInterval(this.interval);
  },
  methods: {
    // handleSpeak(text) {
    //   const synth = window.speechSynthesis;
    //   const msg = new SpeechSynthesisUtterance();
    //   msg.text = text;
    //   msg.lang = "en-US"; //使用的语言
    //   msg.volumn = 1; //声音音量
    //   msg.rate = 1; //语速
    //   msg.pitch = 1; //音高
    //   synth.speak(msg); //播放
    // },
    fetchMessage() {
      setInterval(() => {
        fetch(`http://172.20.10.12:7777/get_message?text=${encodeURIComponent(this.store.text)}`)
            .then(response => response.text())
            .then(data => {
              this.message = data;
              this.handleSpeak(this.message);
            })
            .catch(error => console.error('Error fetching message:', error));
      }, 10000);
    },
    generateRandomHeartRate() {
      const change = Math.trunc((Math.random() * 10) - 5);
      this.heartRate = Math.max(60, Math.min(180, this.heartRate + change));
    },
    fetchAction() {
      this.actionName = this.store.name;
    }
  }
}
</script>

<style scoped>
@keyframes heartbeat {
  0%, 100% {
    transform: scale(1);
  }
  25% {
    transform: scale(1.1);
  }
  50% {
    transform: scale(1.2);
  }
  75% {
    transform: scale(1.1);
  }
}

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
  margin-top: -12%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.action, .heart {
  display: flex;
  align-items: center;
  margin: 0 29px;
}

.heart {
  animation: heartbeat 1s infinite;
}

.warning {
  display: flex;
  align-items: center;
  background-color: #000000;
  border-radius: 37px;
  border: 3px solid #FFFFFF;
  height: 52px;
  padding: 9px 17px;
  max-width: 440px;
}

.action:hover, .warning:hover {
  transform: scale(1.2);
}

.action-icon, .heart-icon, .warning-icon {
  margin-right: 10px;
  height: 37px;
  width: 37px;
}

.custom-text {
  font-size: 27px;
  font-weight: bold;
  color: white;
}

#image-container {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
  width: 720px; /* 设置小窗口的宽度 */
  height: 540px; /* 设置小窗口的高度 */
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 22px;
  margin-bottom: -37px;
}

#image-container img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

/* 视频弹窗样式 */
.popVideo {
  position: absolute;
  float: left;
  width: 2.22rem;
  height: 1.72rem;
  left: 60%;
  top: 1rem;
  z-index: 9999;
  background-color: #fff; /*设置背景色为白色 */
}

.open {
  position: absolute;
  cursor: se-resize;
  height: 0.1rem;
  width: 0.1rem;
  bottom: 0;
  right: 0;
  z-index: 132;

}

.drag {
  position: absolute;
  width: 100%;
  height: 100%;
  padding: 0;
  z-index: 125;
}
</style>