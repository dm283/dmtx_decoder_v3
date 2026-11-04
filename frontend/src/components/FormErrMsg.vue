<script setup>
const emit = defineEmits(['closeModal'])

const props = defineProps({
  errMessageText: {
    type: String,
    required: true
  }
});
</script>

<template>
  <div class="-mt-94 w-96 max-h-4/5 bg-white drop-shadow-md rounded-lg overflow-hidden">
    <header class="py-2 pl-5 bg-red-200 text-lg">
      Ошибка
      <div class="absolute top-2 right-4 cursor-pointer hover:text-gray-500">
        <i class="pi pi-times" style="font-size: 1rem" @click="emit('closeModal')"></i>
      </div>
    </header>
    <div class="my-5 mx-5">
      {{ errMessageText }}
    </div>
  </div>
</template>


<style lang="postcss" scoped>



</style>
