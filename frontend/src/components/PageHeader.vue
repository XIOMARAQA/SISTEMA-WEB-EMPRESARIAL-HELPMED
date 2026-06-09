<script setup>
defineProps({
  title: String,
  subtitle: String,
})
</script>

<template>
  <div class="page-header d-flex justify-content-between align-items-start flex-wrap gap-2">
    <div>
      <h1 class="h3 mb-1 fw-bold text-dark">{{ title }}</h1>
      <p v-if="subtitle" class="text-muted mb-0">{{ subtitle }}</p>
    </div>
    <div><slot name="actions" /></div>
  </div>
</template>
