<template>
  <div>
    <img :src="currentVideoUrl" @error="handleError" alt="Video Stream"/>
  </div>
</template>

<script>
import img from '../assets/img/video-bg.jpg'
export default {
  data() {
    return {
      videoUrl: 'http://172.20.10.12:7777/get_video',
      // fallbackUrl: img,
      currentVideoUrl: '',
    };
  },
  created() {
    this.currentVideoUrl = this.videoUrl;
  },
  methods: {
    handleError() {
      console.log('Error loading video stream, falling back to image');
      // this.currentVideoUrl = this.fallbackUrl;
    },
  },
};

</script>

<style scoped>
img {
  margin-top: 7px;
  width: 100%;
  height: auto;
  border-radius: 8px;
}
</style>

  