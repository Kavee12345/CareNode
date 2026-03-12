import axios from 'axios';

const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';

const instance = axios.create({
  baseURL: BACKEND_URL,
  headers: {
    'Accept': 'application/json',
  },
});

export async function submitIntake(formData) {
  return instance.post('/api/intake', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export async function getDashboard() {
  return instance.get('/api/dashboard');
}
