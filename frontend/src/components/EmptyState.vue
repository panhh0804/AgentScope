<template>
  <div class="empty-state-container">
    <div class="empty-icon-wrapper">
      <svg class="empty-svg" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M20 4H4C2.89543 4 2 4.89543 2 6V18C2 19.1046 2.89543 20 4 20H20C21.1046 20 22 19.1046 22 18V6C22 4.89543 21.1046 4 20 4Z" stroke="#fbbf24" stroke-width="2" stroke-linejoin="round"/>
        <path d="M12 8V12" stroke="#fbbf24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M12 16H12.01" stroke="#fbbf24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <div class="empty-glow"></div>
    </div>
    <div class="empty-title">暂无数据</div>
    <div class="empty-description">
      {{ message || '暂无真实数据，请先启动数据链路或切换 demo 模式。' }}
    </div>
  </div>
</template>

<script>
export default {
  name: 'EmptyState',
  props: {
    message: {
      type: String,
      default: ''
    }
  }
}
</script>

<style scoped>
.empty-state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  width: 100%;
  padding: 40px;
  box-sizing: border-box;
  text-align: center;
}

.empty-icon-wrapper {
  position: relative;
  width: 60px;
  height: 60px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-svg {
  width: 40px;
  height: 40px;
  z-index: 2;
  filter: drop-shadow(0 0 5px rgba(251, 191, 36, 0.4));
}

.empty-glow {
  position: absolute;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: rgba(251, 191, 36, 0.1);
  filter: blur(8px);
}

.empty-title {
  color: #fbbf24;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 10px;
  text-shadow: 0 0 10px rgba(251, 191, 36, 0.2);
}

.empty-description {
  color: #9bc7d9;
  font-size: 14px;
  max-width: 320px;
  line-height: 1.5;
}
</style>
