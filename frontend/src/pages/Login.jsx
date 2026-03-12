import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { LogIn, Mail, Lock, Zap, ChevronRight, Globe, ShieldCheck } from 'lucide-react';
import { motion } from 'framer-motion';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');
    try {
      const success = await login(email, password);
      if (success) {
        navigate('/');
      } else {
        setError('Invalid credentials. Teacher: teacher@college.edu / admin123 | Student: student@student.edu / student123');
      }
    } catch (err) {
      setError('System connection failure. Check backend status.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 relative overflow-hidden">
      {/* Dynamic Background */}
      <div className="absolute top-0 left-0 w-full h-full opacity-10 pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-500 rounded-full blur-[120px]"></div>
        <div className="absolute bottom-[-10%] left-[-10%] w-[50%] h-[50%] bg-purple-500 rounded-full blur-[120px]"></div>
      </div>

      <motion.div 
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-lg glass p-12 rounded-[3.5rem] border-white/60 shadow-2xl relative z-10 mx-6"
      >
        <div className="text-center mb-10">
          <motion.div 
            initial={{ y: -20 }}
            animate={{ y: 0 }}
            className="w-20 h-20 bg-gray-900 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-2xl shadow-gray-900/40"
          >
            <Zap size={40} className="text-white fill-white" />
          </motion.div>
          <h1 className="text-4xl font-black italic tracking-tighter text-gray-900 uppercase mb-2">Campus IQ AI</h1>
          <p className="text-gray-500 font-bold uppercase text-[10px] tracking-[0.3em]">Institutional Intelligence System</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <label className="text-xs font-black uppercase text-gray-500 tracking-widest pl-2 italic">Neural ID / Email</label>
            <div className="glass px-6 py-4 rounded-2xl flex items-center border-white/40 hover:border-blue-300 transition-colors bg-white/30 backdrop-blur-md">
              <Mail className="text-gray-400 mr-4" size={20} />
              <input 
                type="email" 
                placeholder="admin@college.edu" 
                className="bg-transparent border-none outline-none w-full text-gray-900 font-bold"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-black uppercase text-gray-500 tracking-widest pl-2 italic">Cipher / Password</label>
            <div className="glass px-6 py-4 rounded-2xl flex items-center border-white/40 hover:border-blue-300 transition-colors bg-white/30 backdrop-blur-md">
              <Lock className="text-gray-400 mr-4" size={20} />
              <input 
                type="password" 
                placeholder="••••••••" 
                className="bg-transparent border-none outline-none w-full text-gray-900 font-bold"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </div>

          {error && (
            <motion.p 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-red-500 text-xs font-black uppercase tracking-widest text-center"
            >
              {error}
            </motion.p>
          )}

          <button 
            type="submit" 
            disabled={isSubmitting}
            className="w-full bg-gray-900 text-white rounded-3xl py-5 font-black uppercase tracking-[0.3em] shadow-2xl shadow-gray-900/30 hover:bg-black transition transform active:scale-[0.98] flex items-center justify-center space-x-3 group"
          >
            <span>Initiate Link</span>
            <ChevronRight size={20} className="group-hover:translate-x-1 transition-transform" />
          </button>
        </form>

        <div className="mt-12 pt-8 border-t border-gray-200/50 flex justify-between items-center text-[10px] font-black uppercase text-gray-400 tracking-widest">
           <div className="flex items-center">
              <ShieldCheck size={14} className="mr-1 text-blue-500" />
              <span>AES-256 Validated</span>
           </div>
           <div className="flex items-center">
              <Globe size={14} className="mr-1 text-purple-500" />
              <span>v.4.2.0-Legendary</span>
           </div>
        </div>
      </motion.div>
      
      {/* Tech info footer */}
      <div className="absolute bottom-10 text-[9px] font-black uppercase tracking-[0.5em] text-gray-300 text-center w-full">
         Proprietary AI Logic • Unauthorized access is strictly logged
      </div>
    </div>
  );
};

export default Login;
