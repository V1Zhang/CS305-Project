<template>
  <div class="content-box">
    <div class="content">
      <router-view v-slot="{ Component }">
        <transition name="move" mode="out-in">
          <keep-alive>
            <component :is="Component"></component>
          </keep-alive>
        </transition>
      </router-view>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>