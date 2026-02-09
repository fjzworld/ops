import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'element-plus/theme-chalk/dark/css-vars.css'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'
import App from './App.vue'
import router from './router'
import './assets/main.css'
import './assets/design-system.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
