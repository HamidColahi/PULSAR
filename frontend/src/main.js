// ===============================================
// File: Pulsar/frontend/src/main.js
// Description: Application entry point and global UI initialization
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// ===============================================

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import './index.css'
import './assets/styles/theme.css'


const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')