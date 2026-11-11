<script setup>
import {ref, reactive, computed, onMounted} from 'vue';
import axios from 'axios';

const emit = defineEmits(['authOk'])

const login = ref('');
const password = ref('');
const authFormMessage = ref('')

// custom directive for input autofocus
const vFocus = { mounted: (el) => { el.focus() } }

const formLabelStyle = 'mx-1 block text-xs font-bold text-slate-400'
const formInputStyle = 'border-b-2 border-blue-300 text-base w-full py-1 px-1 mb-2 hover:border-blue-400 focus:outline-none focus:border-blue-500 cursor-pointer'


const authSubmit = async () => {
  //
  let formData = new FormData();
  formData.append('username', login.value);
  formData.append('password', password.value);

  try {
    const response_get_token = await axios.post(
      `http://localhost:8000/auth/token`,
      formData, {headers: {'Content-Type': 'multipart/form-data'}});
    if (response_get_token.data.access_token) {
      const response_get_user = await axios.get(`http://localhost:8000/user`, 
        { headers: {Authorization: `Bearer ${response_get_token.data.access_token}`} })
      let uniteUserData = {
        'access_token': response_get_token.data.access_token,
        'login': response_get_user.data.login,
        'role_id': response_get_user.data.role_id,
        'uuid': response_get_user.data.uuid
      }
      localStorage.setItem('userInfo', JSON.stringify(uniteUserData));
      emit('authOk');
    }
  } catch (error) {
    if (error.response) {
      console.log('error status code =', error.response.data.detail)
      if (error.response.status == 401 && error.response.data.detail == 'Incorrect username or password') {
        authFormMessage.value = 'Некорректный логин или пароль.' }
      else if (error.response.status == 403 && error.response.data.detail == 'Username already loged in') {
        authFormMessage.value = `${login.value} залогинен на другом компьютере` }
      else { 
        authFormMessage.value = 'Ошибка авторизации.'
      }  
    }
    
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
      </div>
    </form>
    <div class="mb-5 text-red-500 text-center">
      {{ authFormMessage }}
    </div>
  </div>
</template>


<style lang="postcss" scoped>

</style>
