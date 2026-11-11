<script setup>
// import router from '@/router';
import {ref, reactive, computed, onMounted} from 'vue';
import axios from 'axios';
import FileAttrs from '@/components/FileAttrs.vue'

const userAccessToken = () => {
  let user = JSON.parse(localStorage.getItem('userInfo')); if (user && user.access_token) {return user.access_token} else {return ''}
}

const emit = defineEmits(['clearMsgFile', 'closeModal', 'msgSent'])

const props = defineProps({
  file_for_send: {
    type: File,
    required: true
  },
  user_uuid: {
    type: String,
    required: true
  }
});

const max_cnt_elems = ref(null)

const sendFile = async () => {
  //
  let formData = new FormData();
  formData.append('file', props.file_for_send);
  formData.append('max_cnt_elems', max_cnt_elems.value);
  formData.append('user_uuid', props.user_uuid);
  try {
    const response = await axios.post(`http://localhost:8000/upload_file/`, 
      formData, {headers: {'Content-Type': 'multipart/form-data', Authorization: 'Bearer '+userAccessToken()}});

    emit('msgSent', response.data)
    emit('closeModal')
  } catch (error) {
    console.error('Error uploading file', error);
  };
}

// custom directive for input autofocus
const vFocus = { mounted: (el) => { el.focus() } }

</script>

<template>
  <div class="-mt-70 w-96 max-h-4/5 bg-white drop-shadow-md rounded-lg overflow-hidden">
  
    <header class="py-2 pl-5 bg-slate-200 text-lg">
      Отправить файл
      <div class="absolute top-2 right-4 cursor-pointer hover:text-gray-500">
        <i class="pi pi-times" style="font-size: 1rem" @click="emit('closeModal')"></i>
      </div>
    </header>

    <FileAttrs :file_data="props.file_for_send" class="mt-5 mx-5"/>

    
    <form @submit.prevent="sendFile" enctype="multipart/form-data">
      <div class="mt-5 mx-5">
        <label for="file_caption" class="block mb-1 text-sm font-semibold text-blue-400">max кол-во элементов на странице</label>
        <input v-model="max_cnt_elems" class="w-full h-8 px-2 border-2 border-slate-400 rounded-lg" 
            v-focus :required="true" type="number" min="1" id="file_caption" name="file_caption">
      </div>

      <div class="mt-5 mr-5 mb-5 flex float-right space-x-9 ">
        <button class="text-base font-semibold text-blue-400 cursor-pointer" type="submit">
          Отправить
        </button>
        <button class="text-base font-semibold text-blue-400 cursor-pointer" type="button" @click="emit('clearMsgFile'); emit('closeModal')" >
          Отмена
        </button>
      </div>
    </form>

  </div>

</template>


<style lang="postcss" scoped>



</style>
