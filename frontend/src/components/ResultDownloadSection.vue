<script setup>
import axios from 'axios';

const authHeader = () => {
  let user = JSON.parse(localStorage.getItem('user')); 
  if (user && user.access_token) {return { Authorization: 'Bearer ' + user.access_token };} else {return {};}
}

const props = defineProps({
  processing_path: {
    type: Object,
    required: true
  }
});


async function downloadFile(path, file_name) {
  // downloads file
  let formData = new FormData();
  formData.append('file_path', path);
  formData.append('file_name', file_name);

  let query = `http://localhost:8000/download_file/`
  const response = await axios.post(query, formData, {responseType: "blob", headers: authHeader()});
  const filename = decodeURI(response.headers["file-name"])

  var url = window.URL.createObjectURL(new Blob([response.data]));
  var link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

const iconStyle = 'float-left rounded-lg hover:opacity-70 text-white w-8 h-8 text-center mt-2 pt-[1.5px] cursor-pointer'
// const iconStyle = 'float-left rounded-lg hover:opacity-70 text-white w-8 h-8 text-center mt-2 pt-1.5 cursor-pointer'

</script>

<template>

    <div class="space-x-2">
      <div v-if="props.processing_path.res_csv_file" @click="downloadFile(props.processing_path.res_csv_file, 'res_decoded_dmtx.csv')"
        class="bg-green-300" :class="iconStyle" title="res_decoded_dmtx.csv">
        <!-- <i class="pi pi-file-excel" style="font-size: 1.3rem"></i> -->
         csv
      </div>
      <div v-if="props.processing_path.report_file" @click="downloadFile(props.processing_path.report_file, 'bot_report.txt')"
        class="bg-violet-300" :class="iconStyle" title="bot_report.txt">
        <!-- <i class="pi pi-file-check" style="font-size: 1.3rem"></i> -->
         txt
      </div>
      <div v-if="props.processing_path.undecoded_pages" @click="downloadFile(props.processing_path.undecoded_pages, 'undecoded_pages.zip')"
        class="bg-amber-300" :class="iconStyle" title="undecoded_pages.zip">
        <!-- <i class="pi pi-file-plus" style="font-size: 1.3rem"></i> -->
         zip
      </div>
    </div>

</template>


<style lang="postcss" scoped>

</style>
