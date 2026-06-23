<template>
  <section class="metric-card">
    <div class="metric-icon">
      <component :is="icon" :size="18" />
    </div>
    <div>
      <p class="metric-label">{{ label }}</p>
      <strong class="metric-value">{{ value }}</strong>
      <span v-if="hint" class="metric-hint">{{ hint }}</span>
    </div>
  </section>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  hint: { type: String, default: '' },
  icon: { type: [Object, Function], required: true }
})
</script>

