<template>
  <div class="loading-state-container">
    <div class="loading-spinner">
      <div class="spinner-ring"></div>
      <div class="spinner-glow"></div>
    </div>
    <div class="loading-text">{{ message || '正在加载数据...' }}</div>
  </div>
</template>

<script>
export default {
  name: 'LoadingState',
  props: {
    message: {
      type: String,
      default: ''
    }
  }
}
</script>

<style scoped>
.loading-state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  width: 100%;
  padding: 40px;
  box-sizing: border-box;
}

.loading-spinner {
  position: relative;
  width: 50px;
  height: 50px;
  margin-bottom: 20px;
}

.spinner-ring {
  width: 100%;
  height: 100%;
  border: 3px solid rgba(103, 232, 249, 0.1);
  border-top-color: #67e8f9;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.spinner-glow {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  box-shadow: 0 0 15px rgba(103, 232, 249, 0.5);
  animation: pulse 1.5s ease-in-out infinite alternate;
}

.loading-text {
  color: #9bc7d9;
  font-size: 14px;
  letter-spacing: 1px;
  text-shadow: 0 0 8px rgba(155, 199, 217, 0.3);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  from { opacity: 0.2; }
  to { opacity: 0.6; }
}
</style>
