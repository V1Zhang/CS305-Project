<template>
  <div id="Home_page" style="text-align: center; padding: 5px;">
    <form @submit.prevent="handleSubmit">
      <div id="login_box">
        <br>
        <h1>Remote Meeting</h1>
        <div class="form" style="margin-top: 40px;">
          <input class="form-name" placeholder="username" v-model="username" type="text" autofocus>
        </div>
        <br>
        <h2>Welcome Back!👋</h2>
        <br>
        <button type="submit">LOGIN</button>
      </div>
    </form>
  </div>
</template>

<script>
import {useMainStore} from '../store/data.ts';

const mainStore = useMainStore()
export default {
  data() {
    return {
      username: '',
    };
  },
  methods: {
    handleSubmit() {
      // Handle the form submission logic here
      console.log("Username:", this.username);
      mainStore.login({username: this.username});
      this.$router.push('/mode');
    }
  }
};
</script>

<style scoped>
#Home_page {
  background: url("../assets/img/home_bg.jpg") center; /* 增加背景图 */
  background-size: 100% 100%; /* 设置背景的大小 */
  background-repeat: no-repeat; /* 将背景设置为不重复显示 */
  height: 100vh; /* 设置容器高度为视口高度 */
  display: flex;
  justify-content: center;
  align-items: center;
}

#login_box {
  border: 1px solid white;
  width: 350px;
  text-align: center;
  margin: 0 auto;
  margin-top: 10%; /* 高度调整 */
  background: #00000080;
  padding: 20px 50px;
  /* 将按钮的左右边框设置为圆弧 */
  border-radius: 30px;
  /* 圆角弧度24px */
  transition: 0.2s;
}

#login_box h1 {
  color: white;
}

#login_box h2 {
  color: white;
}

#login_box .form input {
  width: 250px; /* 设置合适的宽度 */
  border: 0; /* 首先将边界取消，方便下面修改下部边界宽度 */
  border-bottom: 4px solid white; /* 将下边界进行修改，显示出横线效果 */
  font-size: 20px; /* 将字体适当的变大加粗 */
  background: #ffffff00; /* 将输入框设置为透明 */
  color: white; /* 上面的文本颜色设置为白色，但是placeholder的颜色要单独设置 */
  padding: 5px 10px; /* 为了placeholder的内容不是顶格显示，增加内部边界 */
}

#login_box button {
  width: 150px;
  text-transform: uppercase;
  border: 3px solid #FFFFFF; /* 设置按钮的边界粗细和颜色 */
  margin-top: 18px; /* 设置合适的上部外框的宽度，增加与上面的password框的距离 */
  text-align: center;
  font-size: 18px; /* 修改按钮文字的大小 */
  color: #FFFFFF;
  line-height: 50px;
  border-radius: 30px; /* 将按钮的左右边框设置为圆弧 */
  cursor: pointer;
  transition: 0.2s;
  background: rgba(0, 0, 0, 0);
}
</style>
