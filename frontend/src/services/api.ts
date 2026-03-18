import axios from 'axios';

const API_URL = 'http://localhost:8000/api/';

const api = axios.create({
    baseURL: API_URL,
});

// INTERCEPTOR: Se ejecuta antes de cada petición
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
        // Adjunta el token JWT siguiendo el estándar Bearer
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
}, (error) => {
    return Promise.reject(error);
});

// Manejo de expiración de token (Opcional pero recomendado)
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            // Si la API dice "No autorizado", limpiamos y mandamos al login
            localStorage.removeItem('access_token');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export default api;