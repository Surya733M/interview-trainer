// services/resumeService.js — Resume API Calls
import api from './api'

export const resumeService = {
  // Upload a PDF resume (multipart form)
  upload: (file, jobTitle) => {
    const formData = new FormData()
    formData.append('file', file)
    if (jobTitle) formData.append('job_title', jobTitle)
    return api.post('/resume/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // List all resumes for current user
  list: () => api.get('/resume/list'),

  // Get a specific resume
  get: (id) => api.get(`/resume/${id}`),

  // Delete a resume
  delete: (id) => api.delete(`/resume/${id}`),
}
