// ===============================================
// File: frontend/src/utils/authToken.js
// Description: Central in-memory JWT access token
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// ===============================================

let accessToken = null


// =================================================
// Token Access
// =================================================

export function setAuthToken(token) {
  accessToken = token || null
}


export function getAuthToken() {
  return accessToken
}


export function clearAuthToken() {
  accessToken = null
}


// Important Learning Points:
// 1. The JWT is kept in memory and is not stored in localStorage.
// 2. authStore and axiosInstance share the token through this module.
// 3. This module prevents a circular dependency between authStore and axiosInstance.
// 4. The token is cleared explicitly during logout.