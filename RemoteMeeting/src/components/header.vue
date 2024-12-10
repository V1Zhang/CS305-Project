<template>
  <div class="header">
    <div class="header-center">
      <div class="header-user-con">
        <div class="welcome-msg">
          <!-- 时间、日期 -->
          <div class="current-time">
            <div class="time">{{ currentTime }}</div>
          </div>
          <div class="current-date">
            <div class="day-date">{{ currentDay }}</div>
            <div class="day-date">{{ currentDate }}</div>
          </div>
          <!-- 天气、位置 -->
          <div class="location-weather">
            <div class="location">
              <img src="../assets/icon/location.svg" alt="location icon" class="location-icon">
              {{ currentLocation }}
            </div>
            <div class="weather">
              <img src="../assets/icon/cloudy.svg" alt="weather icon" class="weather-icon">
              {{ currentWeather }} {{ currentTemperature }}
            </div>
          </div>
          <!-- 用户名 -->
          <div class="username">
            <img src="../assets/icon/user.svg" alt="user icon" class="user-icon">
            Hello, {{ username }} !
          </div>
        </div>
      </div>
    </div>
  </div>
</template>


<script>
import axios from 'axios'
import {useMainStore} from '../store/data';

const mainStore = useMainStore()
export default {
  data() {
    return {
      store: useMainStore(),
      days: ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
      currentLocation: 'Shenzhen',
      currentDate: '',
      currentDay: '',
      currentTime: '',
      currentWeather: 'Cloudy',
      currentTemperature: '27~31°C'
    }
  },
  computed: {
    username() {
      return this.store.username
    }
  },
  created() {
    this.getCurrentLocation()
    this.getCurrentDateTime()
    this.getCurrentWeather()
    this.updateCurrentTime()
  },
  beforeUnmount() {
    clearInterval(this.intervalId)
  },
  methods: {
    getCurrentDateTime() {
      const currentDate = new Date();
      this.currentDate = currentDate.toLocaleDateString();
      this.currentDay = this.days[currentDate.getDay()];
      this.currentTime = currentDate.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        // second: '2-digit',
      });
    },
    updateCurrentTime() {
      this.intervalId = setInterval(() => {
        this.getCurrentDateTime()
      }, 1000)
    },
    getCurrentWeather() {
      // 使用第三方API获取当前天气信息
      // axios.get('/api/weather')
      //   .then(response => {
      //     this.currentWeather = response.data.weather
      //   })
      //   .catch(error => {
      //     console.error('Error fetching weather:', error)
      //   })
    },
    getCurrentLocation() {
      // 使用浏览器地理位置API获取当前位置
      // if (navigator.geolocation) {
      //   navigator.geolocation.getCurrentPosition(
      //     position => {
      //       // 根据经纬度获取城市信息
      //       this.fetchLocationData(position.coords.latitude, position.coords.longitude);
      //     },
      //     error => {
      //       console.error('Error getting location:', error);
      //       this.currentLocation = 'Beijing';
      //     }
      //   );
      // } else {
      //   console.error('Geolocation is not supported by this browser.');
      //   this.currentLocation = 'Beijing';
      // }
    },

    fetchLocationData(latitude, longitude) {
      axios.get(`/api/location?lat=${latitude}&lon=${longitude}`)
          .then(response => {
            this.currentLocation = response.data.city;
          })
          .catch(error => {
            console.error('Error fetching location:', error);
            this.currentLocation = '无法获取城市信息';
          });
    }
  }
}
</script>


<style scoped>
.header {
  background-color: black;
  position: relative;
  box-sizing: border-box;
  width: 100%;
  height: 70px;
  font-size: 22px;
  color: #fff;
  justify-content: center; /* 水平居中 */
  align-items: center; /* 垂直居中 */
  display: flex;
}

.header .current-time {
  width: 140px;
  font-size: 35px;
}

.header .current-date {
  width: 140px;
  font-size: 20px;
}

.header .location-weather {
  width: 200px;
  font-size: 20px;
}

.location-icon {
  margin-top: 3px;
  height: 25px;
  vertical-align: top; /* 垂直居中对齐 */
  width: 25px;
}

.weather-icon {
  margin-top: 3px;
  height: 22px;
  vertical-align: top; /* 垂直居中对齐 */
}

.user-icon {
  height: 30px;
  vertical-align: top; /* 垂直居中对齐 */
}

.header-center {
  float: right;
}

.header-user-con {
  display: flex;
  height: 70px;
  align-items: center;
}

.username {
  margin-left: 10px;
}

.welcome-msg {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.welcome-msg > span {
  margin: 0 10px;
}
</style>