<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import axios from 'axios';
import 'primeicons/primeicons.css';
import FormSendFile from './components/FormSendFile.vue'
import FileAttrs from './components/FileAttrs.vue'
import ResultDownloadSection from './components/ResultDownloadSection.vue'
import FormErrMsg from './components/FormErrMsg.vue'
import AuthForm from './components/AuthForm.vue'

const authHeader = () => {
  let user = JSON.parse(localStorage.getItem('userInfo')); 
  if (user && user.access_token) {return { Authorization: 'Bearer ' + user.access_token };} else {return {};}
}


const isAuthorized = ref(false)
const showFromSendFile = ref(false);
const showErrMsg = ref(false);
const errMessageText = ref('');
const file = ref('')
const fileForSend = ref('')
const sentFilesList = ref([])
const userInfo = ref()


const initApp = async () => {
  //
  console.log('init app')
  getUserInfo();
  console.log('getuserinfo done', userInfo.value)
  if (!userInfo.value) { return }
  getUserTasks();
  console.log('getusertasks done', sentFilesList.value)
  initWS(userInfo.value.uuid);
  console.log('initws done')
  isAuthorized.value = true;
}


const getUserInfo = async () => {
  userInfo.value = JSON.parse(localStorage.getItem('userInfo'));
}


const getUserTasks = async () => {
  //
  try {     
    const response = await axios.get(`http://localhost:8000/user_tasks`, {headers: authHeader()});
    console.log('loaded tasks =', response.data)
    sentFilesList.value = response.data;
    console.log('sentFilesList =', sentFilesList.value[0])
  } catch (error) {
    // unauthorized response (obsolete token)
    if (error.response.status == 401 && error.response.data.detail == 'Could not validate credentials') {
      signOut()
    }
    // if (error.status == 401 ) { 
    //   console.error('unauthorized'); 
    // }
    console.error('Error fetching', error);
  } 
}


const initWS = ( user_uuid ) => {
  // console.log('auth ok - open websock')
  console.log('inside initws =', user_uuid)
  // const ws = new WebSocket(`ws://localhost:8000/ws/${userInfo.value.uuid}`);
  const ws = new WebSocket(`ws://localhost:8000/ws/${user_uuid}`);
  // const ws = new WebSocket(`ws://localhost:8000/ws/frontend`);
  ws.onmessage = function(event) {
    // const message = event.data  // 
    const message = JSON.parse(event.data);
    // messages.value.push(message);
    if (message.message=='recognition done') {
      for (let sf in sentFilesList.value) {
        if (sentFilesList.value[sf].uuid==message.uuid) {
          sentFilesList.value[sf].status = 'готово'
          sentFilesList.value[sf].finish_time = message.finish_time
          sentFilesList.value[sf].processing_path = message.processing_path
        } } }
    else if (message.message=='error') {
      for (let sf in sentFilesList.value) {
        if (sentFilesList.value[sf].uuid==message.uuid) {
          sentFilesList.value[sf].status = 'ошибка'
          sentFilesList.value[sf].finish_time = message.finish_time
        } } }
    else if (message.message=='zero') {
      for (let sf in sentFilesList.value) {
        if (sentFilesList.value[sf].uuid==message.uuid) {
          sentFilesList.value[sf].status = 'нераспознано'
          sentFilesList.value[sf].finish_time = message.finish_time
        } } }    
  };
}


const pasteFile = async (event) => {
  const data = event.clipboardData;
  fileForSend.value = data && data.files && data.files[0];
  event.target.blur();
  openSendForm()
}


const openSendForm = () => {
  if (fileForSend.value.type != 'application/pdf') { 
    errMessageText.value = 'Не pdf файл.'; showErrMsg.value = true; return 
  }
  showFromSendFile.value = true
}


const sentFilesListAdd = async (sentFile) => {
  //sentFilesList.value.push(sentFile)
  sentFilesList.value.unshift(sentFile)
}


const setStatusStyle = (status) => {
  if (status == 'в обработке') { return 'mt-3 ml-18 text-blue-500' }
  else if (status == 'ошибка') { return 'mt-3 ml-18 text-red-500' }
  else if (status == 'нераспознано') { return 'mt-3 ml-18 text-yellow-900' }
}


const processing_path_to_obj = (processing_path) => {
  //
  if (typeof processing_path == 'string') { return JSON.parse(processing_path) }
  return processing_path
}


const signOut = async () => {
  //
  localStorage.removeItem('userInfo');
  isAuthorized.value = false;
  sentFilesList.value.length = 0;
};


onMounted( () => {
  initApp()
});

</script>

<template>

  <div v-if="!isAuthorized" class="">
    <AuthForm @auth-ok="initApp()"/>
  </div>


  <div v-if="isAuthorized">

  <header class="h-10 py-1.5 px-10 bg-blue-500 text-white text-lg bg-gradient-to-r from-blue-500 to-sky-500">
    datamatrix decoder v.3
      <div class="float-right mx-3 mt-1 text-cyan-200 cursor-pointer hover:text-cyan-50" title='sign out'>
        <i class="pi pi-sign-out" style="font-size: 1.3rem" @click="signOut()"></i></div>
      <div class="float-right mt-0.5 mr-5 text-base">{{ userInfo.login }}</div>
  </header>

  <section class="flex mx-auto w-fit mt-20 p-1.5">
    <div class="mr-2">
      <label for="msg_add_file" class="cursor-pointer hover:text-slate-500" title="прикрепить файл"><i class="pi pi-paperclip" style="font-size: 1.8rem"></i></label>
      <input class="hidden" type="file" ref="file" id="msg_add_file" name="msg_add_file" 
        @change="fileForSend=file.files[0]; openSendForm()">
    </div>
    <input type="text" id="msg_input_field" name="msg_input_field" placeholder="paste pdf file here..."
      @paste="pasteFile"
      class="w-80 h-8 px-2 border-2 border-slate-400 rounded-lg" >
  </section>

  <div v-if="showFromSendFile" class="absolute z-10 top-0 left-0 w-full h-full bg-black/50 flex items-center justify-center">
    <FormSendFile @close-modal="showFromSendFile=false" @clear-msg-file="file.value=''" @msg-sent="sentFilesListAdd" 
      :file_for_send="fileForSend" :user_uuid="userInfo.uuid" />
  </div>

  <div v-if="showErrMsg" class="absolute z-10 top-0 left-0 w-full h-full bg-black/50 flex items-center justify-center">
    <FormErrMsg @close-modal="showErrMsg=false" :errMessageText="errMessageText" />
  </div>

  <section v-if="sentFilesList.length>0" class="m-auto mt-5 w-fit space-y-3">
    <div v-for="sfile in sentFilesList" class="w-[528px] h-17 p-2 border border-slate-200 rounded-md">
      <!-- <div class="float-left w-60 overflow-hidden mr-5"><FileAttrs :file_data="sfile.file" /></div> -->
      <div class="float-left w-60 overflow-hidden mr-5"><FileAttrs :file_data="{'filename':sfile.filename, 'size':sfile.size}" /></div>
      <div class=" float-left w-12 mt-4 text-xs font-semibold text-slate-500">{{ sfile.start_time }}</div>
      <div class=" float-left w-12 mt-4 mx-5 text-xs font-semibold text-center text-slate-500">{{ sfile.finish_time || '-'}}</div>
      <div v-if="sfile.status!='готово'" :class=setStatusStyle(sfile.status)>{{ sfile.status }}</div>
      <ResultDownloadSection :processing_path=processing_path_to_obj(sfile.processing_path) v-if="sfile.status=='готово'" class="ml-5" />
      <!-- <ResultDownloadSection :processing_path='sfile.processing_path' v-if="sfile.status=='done'" class="ml-5" /> -->
    </div>

  </section>

  </div>
</template>

<style scoped>

</style>
