<script setup>

const props = defineProps({
  file_data: {
    type: Object,
    required: true
  }
});

</script>

<template>

    <!-- <div class="flex">
      <div class="rounded-full bg-blue-400 text-white w-12 text-center pt-2"><i class="pi pi-file" style="font-size: 1.8rem"></i></div>
      <div class="ml-3">
        <div class="border text-base font-semibold max-w-68 truncate">{{ props.file_data.name || props.file_data.filename }}</div>
        <div class="text-base text-slate-500">{{ Number((props.file_data.size/1000).toPrecision(1)) }} KB</div>
      </div>
    </div> -->

    <div class="">
      <div class="float-left mr-3 rounded-full bg-blue-400 text-white w-12 h-12 text-center pt-2">
        <i class="pi pi-file" style="font-size: 1.8rem"></i></div>
      <div class="">
        <div class="text-base font-semibold max-w-68 truncate">{{ props.file_data.name || props.file_data.filename }}</div>
        <div class="text-base text-slate-500">{{ Number((props.file_data.size/1000).toPrecision(1)) }} KB</div>
      </div>
    </div>

</template>


<style lang="postcss" scoped>



</style>
