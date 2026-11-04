<script setup>
import { ref } from 'vue';
import axios from 'axios';
import 'primeicons/primeicons.css';
import FormSendFile from './components/FormSendFile.vue'
import FileAttrs from './components/FileAttrs.vue'
import ResultDownloadSection from './components/ResultDownloadSection.vue'
import FormErrMsg from './components/FormErrMsg.vue'



const ws = new WebSocket(`ws://localhost:8000/ws/10`);
ws.onmessage = function(event) {
  // const message = event.data  // 
  const message = JSON.parse(event.data);
  // messages.value.push(message);
  if (message.message=='recognition done') {
    for (let sf in sentFilesList.value) {
      if (sentFilesList.value[sf].uuid==message.uuid) {
        sentFilesList.value[sf].file_data.status = 'done'
        sentFilesList.value[sf].file_data.finish_time = message.finish_time
        sentFilesList.value[sf].file_data.processing_path = message.processing_path
      } } }
  else if (message.message=='error') {
    for (let sf in sentFilesList.value) {
      if (sentFilesList.value[sf].uuid==message.uuid) {
        sentFilesList.value[sf].file_data.status = 'ошибка'
        sentFilesList.value[sf].file_data.finish_time = message.finish_time
      } } }    
};

const showFromSendFile = ref(false);
const showErrMsg = ref(false);
const errMessageText = ref('');
const file = ref('')
const fileForSend = ref('')
const sentFilesList = ref([])

const openSendForm = () => {
  if (fileForSend.value.type != 'application/pdf') { 
    errMessageText.value = 'Не pdf файл.'; showErrMsg.value = true; return 
  }
  showFromSendFile.value = true
}


const pasteFile = async (event) => {
  const data = event.clipboardData;
  fileForSend.value = data && data.files && data.files[0];
  event.target.blur();
  openSendForm()
}


const sentFilesListAdd = async (sentFile) => {
  //sentFilesList.value.push(sentFile)
  sentFilesList.value.unshift(sentFile)
}


const setStatusStyle = (status) => {
  if (status == 'в обработке') { return 'mt-3 ml-18 text-blue-500' }
  else if (status == 'ошибка') { return 'mt-3 ml-18 text-red-500' }
}


</script>

<template>
  <header class="flex h-10 py-1.5 pl-10 bg-blue-500 text-white bg-gradient-to-r from-blue-500 to-sky-500">
    datamatrix decoder v.3
  </header>
 
  <section class="flex mx-auto w-fit mt-20 p-1.5">
    <div class="mr-2">
      <label for="msg_add_file" class="cursor-pointer hover:text-slate-500"><i class="pi pi-paperclip" style="font-size: 1.8rem"></i></label>
      <input class="hidden" type="file" ref="file" id="msg_add_file" name="msg_add_file" 
        @change="fileForSend=file.files[0]; openSendForm()">
    </div>
    <input type="text" id="msg_input_field" name="msg_input_field" placeholder="paste pdf file here..."
      @paste="pasteFile"
      class="w-80 h-8 px-2 border-2 border-slate-400 rounded-lg" >
  </section>

  <div v-if="showFromSendFile" class="absolute z-10 top-0 left-0 w-full h-full bg-black/50 flex items-center justify-center">
    <FormSendFile @close-modal="showFromSendFile=false" @clear-msg-file="file.value=''" @msg-sent="sentFilesListAdd" 
      :file_for_send="fileForSend" />
  </div>

  <div v-if="showErrMsg" class="absolute z-10 top-0 left-0 w-full h-full bg-black/50 flex items-center justify-center">
    <FormErrMsg @close-modal="showErrMsg=false" :errMessageText="errMessageText" />
  </div>

  <section v-if="sentFilesList.length>0" class="m-auto mt-5 w-fit space-y-3">
    <div v-for="sfile in sentFilesList" class="w-[528px] h-17 p-2 border border-slate-200 rounded-md">
      <div class="float-left w-60 overflow-hidden mr-5"><FileAttrs :file_data="sfile.file_data.file" /></div>
      <div class=" float-left w-12 mt-4 text-xs font-semibold text-slate-500">{{ sfile.file_data.sent_dt }}</div>
      <div class=" float-left w-12 mt-4 mx-5 text-xs font-semibold text-center text-slate-500">{{ sfile.file_data.finish_time || '-'}}</div>
      <div v-if="sfile.file_data.status!='done'" :class=setStatusStyle(sfile.file_data.status)>{{ sfile.file_data.status }}</div>
      <ResultDownloadSection :processing_path='sfile.file_data.processing_path' v-if="sfile.file_data.status=='done'" class="ml-5" />
    </div>

  </section>

</template>

<style scoped>

</style>
