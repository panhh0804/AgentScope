<template>
  <div class="error-state-container">
    <div class="error-icon-wrapper">
      <svg class="error-svg" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="#fb7185" stroke-width="2" stroke-linejoin="round"/>
        <path d="M15 9L9 15" stroke="#fb7185" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M9 9L15 15" stroke="#fb7185" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <div class="error-glow"></div>
    </div>
    <div class="error-title">数据服务暂不可用</div>
    <div class="error-reason" v-if="reason">
      <span class="reason-label">异常原因:</span> {{ reason }}
    </div>
    <button class="retry-button" @click="$emit('retry')" v-if="showRetry">
      尝试重新加载
    </button>
  </div>
</template>

<script>
export default {
  name: 'ErrorState',
  props: {
    reason: {
      type: String,
      default: ''
    },
    showRetry: {
      type: Boolean,
      default: true
    }
  }
}
</script>

<style scoped>
.error-state-container {
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

.error-icon-wrapper {
  position: relative;
  width: 60px;
  height: 60px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-svg {
  width: 40px;
  height: 40px;
  z-index: 2;
  filter: drop-shadow(0 0 5px rgba(251, 113, 133, 0.4));
}

.error-glow {
  position: absolute;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: rgba(251, 113, 133, 0.1);
  filter: blur(8px);
}

.error-title {
  color: #fb7185;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 10px;
  text-shadow: 0 0 10px rgba(251, 113, 133, 0.2);
}

.error-reason {
  color: #9bc7d9;
  font-size: 13px;
  max-width: 380px;
  line-height: 1.5;
  background: rgba(251, 113, 133, 0.05);
  border: 1px solid rgba(251, 113, 133, 0.15);
  border-radius: 4px;
  padding: 8px 12px;
  margin-bottom: 15px;
}

.reason-label {
  color: rgba(251, 113, 133, 0.85);
  font-weight: 500;
}

.retry-button {
  background: rgba(251, 113, 133, 0.1);
  border: 1px solid rgba(251, 113, 133, 0.4);
  color: #fb7185;
  padding: 6px 16px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.retry-button:hover {
  background: rgba(251, 113, 133, 0.2);
  border-color: #fb7185;
  box-shadow: 0 0 8px rgba(251, 113, 133, 0.3);
}
</style>
