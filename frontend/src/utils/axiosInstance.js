// ================================================
// File: frontend/src/utils/axiosInstance.js
// Description: Central Axios instance for Pulsar API communication
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// ================================================

import axios from 'axios'

import {
  getAuthToken
} from '@/utils/authToken'


// =================================================
// Axios Instance
// =================================================

const axiosInstance = axios.create({
  baseURL: 'http://localhost:8000/',
  timeout: 10000,
})


// =================================================
// Request Interceptor
// =================================================
//
// Authentication is applied centrally here.
//
// API consumers such as:
//   useContextAccess
//   useUserAccess
//   useComponentData
//   generic_page
//
// do not need to know anything about JWT.
//

axiosInstance.interceptors.request.use(
  config => {

    const token =
      getAuthToken()

    if (token) {

      config.headers =
        config.headers || {}

      config.headers.Authorization =
        `Bearer ${token}`
    }

    return config
  },

  error => {
    return Promise.reject(error)
  }
)


export default axiosInstance


// Important Learning Points:
// 1. axiosInstance remains the single HTTP entry point for Pulsar.
// 2. Backend URL remains centralized in this file.
// 3. JWT is automatically attached to authenticated requests.
// 4. API consumers do not handle Authorization headers directly.
// 5. The JWT is not stored in localStorage by this HTTP layer.
// 6. Changing the Backend URL still requires changing only this configuration point.