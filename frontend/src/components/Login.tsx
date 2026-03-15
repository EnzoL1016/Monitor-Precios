import React, { useState } from 'react';
import api from '../services/api';
import { LogIn, UserPlus, Loader2, AlertCircle, Check } from 'lucide-react';

interface LoginProps {
    onLoginSuccess: () => void;
}



export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
    const [mode, setMode] = useState<'login' | 'register'>('login');

    // Login fields
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');

    // Register fields
    const [regUsername, setRegUsername] = useState('');
    const [regEmail, setRegEmail] = useState('');
    const [regPassword, setRegPassword] = useState('');

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [successMsg, setSuccessMsg] = useState('');

    const resetFields = () => {
        setUsername(''); setPassword('');
        setRegUsername(''); setRegEmail(''); setRegPassword('');
        setError(''); setSuccessMsg('');
    };

    const switchMode = (newMode: 'login' | 'register') => {
        resetFields();
        setMode(newMode);
    };

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            const response = await api.post('token/', { username, password });
            localStorage.setItem('access_token', response.data.access);
            localStorage.setItem('refresh_token', response.data.refresh);
            onLoginSuccess();
        } catch {
            setError('Usuario o contraseña incorrectos.');
        } finally {
            setLoading(false);
        }
    };

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        setSuccessMsg('');
        try {
            await api.post('register/', {
                username: regUsername,
                email: regEmail,
                password: regPassword,
            });
            // Loguear automáticamente tras registrar
            const tokenRes = await api.post('token/', {
                username: regUsername,
                password: regPassword,
            });
            localStorage.setItem('access_token', tokenRes.data.access);
            localStorage.setItem('refresh_token', tokenRes.data.refresh);
            onLoginSuccess();
        } catch (err: any) {
            const msg = err.response?.data?.error || 'Error al registrarse. Verificá los datos.';
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-[#0f0f10] p-4">
            <div className="max-w-md w-full">
                {/* Logo / título */}
                <div className="text-center mb-8">
                    <div className="bg-gradient-to-br from-blue-600 to-blue-800 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-xl shadow-blue-900/30">
                        {mode === 'login' ? <LogIn className="text-white" size={30} /> : <UserPlus className="text-white" size={30} />}
                    </div>
                    <h1 className="text-3xl font-black text-white tracking-tight">PriceMonitor</h1>
                    <p className="text-gray-500 text-sm mt-1">
                        {mode === 'login' ? 'Ingresá para gestionar tus monitores' : 'Creá tu cuenta gratuita'}
                    </p>
                </div>

                {/* Card */}
                <div className="bg-[#1e1f20] rounded-3xl border border-[#37393b] p-8 shadow-2xl">

                    {/* Tabs */}
                    <div className="flex bg-[#131314] rounded-2xl p-1 mb-7 gap-1">
                        <button
                            onClick={() => switchMode('login')}
                            className={`flex-1 py-2.5 rounded-xl text-sm font-bold transition-all ${mode === 'login' ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-500 hover:text-gray-300'}`}
                        >
                            Iniciar Sesión
                        </button>
                        <button
                            onClick={() => switchMode('register')}
                            className={`flex-1 py-2.5 rounded-xl text-sm font-bold transition-all ${mode === 'register' ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-500 hover:text-gray-300'}`}
                        >
                            Registrarse
                        </button>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="mb-5 p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl flex items-center gap-3 text-sm">
                            <AlertCircle size={16} className="shrink-0" /> {error}
                        </div>
                    )}

                    {/* Success */}
                    {successMsg && (
                        <div className="mb-5 p-4 bg-green-500/10 border border-green-500/20 text-green-400 rounded-xl flex items-center gap-3 text-sm">
                            <Check size={16} className="shrink-0" /> {successMsg}
                        </div>
                    )}

                    {/* LOGIN FORM */}
                    {mode === 'login' && (
                        <form onSubmit={handleLogin} className="space-y-4">
                            <div>
                                <label className="block text-xs font-black uppercase text-gray-500 mb-2 tracking-widest">Usuario</label>
                                <input
                                    type="text" required autoComplete="username"
                                    className="w-full p-4 rounded-2xl bg-[#131314] border border-[#37393b] text-[#e3e3e3] placeholder:text-gray-600 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-black uppercase text-gray-500 mb-2 tracking-widest">Contraseña</label>
                                <input
                                    type="password" required autoComplete="current-password"
                                    className="w-full p-4 rounded-2xl bg-[#131314] border border-[#37393b] text-[#e3e3e3] placeholder:text-gray-600 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                            </div>
                            <button
                                type="submit" disabled={loading}
                                className="w-full bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-2xl font-bold transition-all flex justify-center items-center gap-2 shadow-lg shadow-blue-900/30 disabled:opacity-50 active:scale-95 mt-2"
                            >
                                {loading ? <Loader2 className="animate-spin" size={20} /> : 'Iniciar Sesión'}
                            </button>
                        </form>
                    )}

                    {/* REGISTER FORM */}
                    {mode === 'register' && (
                        <form onSubmit={handleRegister} className="space-y-4">
                            <div>
                                <label className="block text-xs font-black uppercase text-gray-500 mb-2 tracking-widest">Nombre de Usuario</label>
                                <input
                                    type="text" required autoComplete="username"
                                    placeholder="ej: juan123"
                                    className="w-full p-4 rounded-2xl bg-[#131314] border border-[#37393b] text-[#e3e3e3] placeholder:text-gray-600 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all"
                                    value={regUsername}
                                    onChange={(e) => setRegUsername(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-black uppercase text-gray-500 mb-2 tracking-widest">Correo Electrónico</label>
                                <input
                                    type="email" required autoComplete="email"
                                    placeholder="tu@correo.com"
                                    className="w-full p-4 rounded-2xl bg-[#131314] border border-[#37393b] text-[#e3e3e3] placeholder:text-gray-600 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all"
                                    value={regEmail}
                                    onChange={(e) => setRegEmail(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-black uppercase text-gray-500 mb-2 tracking-widest">Contraseña</label>
                                <input
                                    type="password" required autoComplete="new-password"
                                    placeholder="Mínimo 8 caracteres"
                                    className="w-full p-4 rounded-2xl bg-[#131314] border border-[#37393b] text-[#e3e3e3] placeholder:text-gray-600 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all"
                                    value={regPassword}
                                    onChange={(e) => setRegPassword(e.target.value)}
                                />
                            </div>
                            <button
                                type="submit" disabled={loading}
                                className="w-full bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-2xl font-bold transition-all flex justify-center items-center gap-2 shadow-lg shadow-blue-900/30 disabled:opacity-50 active:scale-95 mt-2"
                            >
                                {loading ? <Loader2 className="animate-spin" size={20} /> : 'Crear Cuenta'}
                            </button>
                        </form>
                    )}
                </div>

                <p className="text-center text-gray-600 text-xs mt-6">
                    PriceMonitor © {new Date().getFullYear()} · Monitoreo de precios automatizado
                </p>
            </div>
        </div>
    );
};