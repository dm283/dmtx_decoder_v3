<script setup>
import {ref, reactive, computed, onMounted} from 'vue';
import axios from 'axios';

const authHeader = () => {
  let user = JSON.parse(localStorage.getItem('user')); 
  if (user && user.access_token) {return { Authorization: 'Bearer ' + user.access_token };} else {return {};}
}

const emit = defineEmits(['authOk'])

const login = ref('');
const password = ref('');
const authFormMessage = ref('')

// const props = defineProps({
//   file_for_send: {
//     type: File,
//     required: true
//   }
// });



// custom directive for input autofocus
const vFocus = { mounted: (el) => { el.focus() } }

const formLabelStyle = 'mx-1 block text-xs font-bold text-slate-400'
const formInputStyle = 'border-b-2 border-blue-300 text-base w-full py-1 px-1 mb-2 hover:border-blue-400 focus:outline-none focus:border-blue-500 cursor-pointer'

const setUserInfo = async () => {
  //
  const response = await axios.get(`http://localhost:8000/user`, {headers: authHeader()})
  //state.userInfo = response.data  //
  console.log('get user =', response.data)
  localStorage.setItem('userInfo', JSON.stringify(response.data));
}


const authSubmit = async () => {
  //
  let formData = new FormData();
  formData.append('username', login.value);
  formData.append('password', password.value);

  try {
    const response = await axios.post(
      `http://localhost:8000/auth/token`,
      formData, {headers: {'Content-Type': 'multipart/form-data'}});
    if (response.data.access_token) {
      localStorage.setItem('user', JSON.stringify(response.data));
      emit('authOk')
      // isAuthorized.value = true;
      // state.isLoading = true;
      await setUserInfo();
    }
  } catch (error) {
    authFormMessage.value = 'Некорректный логин или пароль.'
    // isAuthorized.value = false;
  };
}

</script>

<template>
  <div class="w-80 mt-40 mx-auto border border-slate-300 rounded-lg overflow-hidden">
    <div class="py-2 px-5 bg-gradient-to-r from-blue-500 to-sky-500 text-left text-white text-lg">
      datamatrix decoder v.3
    </div>
    <form @submit.prevent="authSubmit" class="mx-5 mt-5">
      <div class="my-2">
        <label :class=formLabelStyle>Логин</label>
        <input type="text" v-model="login" id="login" name="login" :class=formInputStyle required v-focus />
      </div>
      <div class="my-2">
        <label :class=formLabelStyle>Пароль</label>
        <input type="password" v-model="password" id="password" name="password" :class=formInputStyle required />
      </div>
      <div class="mt-5 mb-6 text-center">
        <button
          class="text-slate-400 text-sm font-semibold border border-slate-400 rounded-lg w-32 h-9 hover:text-slate-500 hover:border-slate-500 cursor-pointer"
          type="submit"
        >
        ВХОД
        </button>
        <!-- bg-green-500 text-white font-semibold rounded-full px-3 py-2 w-60 shadow-md hover:shadow-lg hover:bg-green-600 -->
      </div>
    </form>
    <div class="mb-5 text-red-500 text-center">
      {{ authFormMessage }}
    </div>
  </div>
</template>


<style lang="postcss" scoped>

</style>
