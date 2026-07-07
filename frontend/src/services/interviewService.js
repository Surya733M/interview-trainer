// services/interviewService.js — Interview API Calls
import api from './api'

export const interviewService = {
  // Start a new mock interview
  start: (data) => api.post('/interview/start', data),

  // Submit an answer
  answer: (data) => api.post('/interview/answer', data),

  // Get interview session
  get: (id) => api.get(`/interview/${id}`),

  // List all interviews
  list: () => api.get('/interview/list'),
}
