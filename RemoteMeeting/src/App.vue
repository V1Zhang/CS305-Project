<template>
  <el-config-provider class="home" :locale="zhCn">
    <router-view/>
  </el-config-provider>
</template>

<script setup lang="ts">
import {ElConfigProvider} from 'element-plus';
import zhCn from 'element-plus/es/locale/lang/zh-cn'
</script>

<style lang="scss">
@import './assets/font/font.css';
#app {
  font-family: Chalkboard,sans-serif;
}
.home{
  font-family: Chalkboard,sans-serif;
}
</style>