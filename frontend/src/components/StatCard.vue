<script setup>
defineProps({
  label: String,
  value: [String, Number],
  icon: String,
  variant: { type: String, default: '' },
  hint: { type: String, default: '' },
})
</script>

<template>
  <div class="card stat-card h-100" :class="variant">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-start">
        <div>
          <div class="text-muted small text-uppercase">{{ label }}</div>
          <div class="fs-3 fw-bold mt-1">{{ value ?? 0 }}</div>
          <div v-if="hint" class="small text-muted mt-1">{{ hint }}</div>
        </div>
        <div class="text-primary opacity-75 fs-4">
          <i :class="['bi', icon]"></i>
        </div>
      </div>
      <slot />
    </div>
  </div>
</template>
