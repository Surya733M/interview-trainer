// services/authService.js — Auth API Calls
import api from './api'

export const authService = {
  // Register a new account
  register: (data) => api.post('/auth/register', data),

  // Login and get JWT token
  login: (data) => api.post('/auth/login', data),

  // Logout (tells server, but token is cleared client-side)
  logout: () => api.post('/auth/logout'),

  // Get current user profile
  getMe: () => api.get('/auth/me'),
}
