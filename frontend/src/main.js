import { createApp } from 'vue'
import ArcoVue from '@arco-design/web-vue'
import '@arco-design/web-vue/dist/arco.css'
import App from './App.vue'
import router from './router'
import './style.css'

document.body.setAttribute('arco-theme', 'dark')

createApp(App).use(router).use(ArcoVue).mount('#app')
