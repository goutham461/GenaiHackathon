import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Award, CheckCircle, Search, ExternalLink, ShieldCheck, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';

const Scholarships = () => {
  const [schemes, setSchemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rollNo, setRollNo] = useState('');
  const [eligible, setEligible] = useState(null);

  useEffect(() => {
    fetchSchemes();
  }, []);

  const fetchSchemes = async () => {
    try {
      const res = await api.get('/scholarships/');
      setSchemes(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const checkEligibility = async () => {
    if (!rollNo) return;
    try {
      const res = await api.get(`/scholarships/eligible/${rollNo}/`);
      setEligible(res.data.eligible_schemes);
    } catch (err) {
      console.error(err);
      setEligible([]);
    }
  };

  return (
    <div className="p-8 space-y-8 min-h-screen bg-gray-50/50">
      <motion.div 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
      >
        <h2 className="text-3xl font-bold text-gray-900">Scholarship Portal</h2>
        <p className="text-gray-500">Intelligent matching for government and institutional grants.</p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <motion.div
           initial={{ opacity: 0, y: 20 }}
           animate={{ opacity: 1, y: 0 }}
           className="glass p-8 rounded-[2.5rem] border-white/40 shadow-sm overflow-hidden relative"
        >
          <div className="absolute top-0 right-0 p-8">
            <ShieldCheck size={120} className="text-blue-500/5 rotate-12" />
          </div>

          <div className="relative">
            <h3 className="text-xl font-bold text-gray-900 mb-6">Eligibility Checker</h3>
            <p className="text-sm text-gray-500 mb-8 max-w-sm">Enter a student roll number to check real-time eligibility based on income, caste, and performance.</p>
            
            <div className="flex flex-col space-y-4">
              <div className="flex space-x-2">
                <div className="flex-1 glass px-4 py-3 rounded-2xl flex items-center border-white/40 shadow-inner">
                   <Search size={18} className="text-gray-400 mr-3" />
                   <input 
                    type="text" 
                    placeholder="Enter Roll No (e.g. CS1001)" 
                    className="bg-transparent border-none outline-none w-full text-gray-900 font-mono font-bold uppercase"
                    value={rollNo}
                    onChange={(e) => setRollNo(e.target.value)}
                  />
                </div>
                <button 
                  onClick={checkEligibility}
                  className="bg-blue-600 text-white px-6 py-3 rounded-2xl font-bold shadow-lg shadow-blue-500/20 hover:bg-blue-700 transition"
                >
                  Verify
                </button>
              </div>

              {eligible !== null && (
                <motion.div 
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="pt-6 border-t border-gray-100"
                >
                  <h4 className="font-bold text-gray-900 mb-4 flex items-center space-x-2">
                    <CheckCircle size={18} className="text-green-500" />
                    <span>Eligible Schemes:</span>
                  </h4>
                  {eligible.length > 0 ? (
                    <div className="space-y-3">
                      {eligible.map((s, idx) => (
                        <div key={idx} className="flex items-center justify-between p-4 bg-green-50 rounded-2xl border border-green-100">
                          <span className="font-bold text-green-700">{s}</span>
                          <button className="text-green-600 hover:text-green-800 flex items-center space-x-1 text-xs font-black uppercase tracking-widest">
                            <span>Apply</span>
                            <ChevronRight size={14} />
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-4 bg-gray-50 rounded-2xl text-gray-500 text-sm font-medium">
                      Student is not currently eligible for any active scholarship schemes.
                    </div>
                  )}
                </motion.div>
              )}
            </div>
          </div>
        </motion.div>

        <div className="space-y-6">
          <h3 className="text-xl font-bold text-gray-900 px-2">Active Schemes</h3>
          <div className="space-y-4">
            {loading ? (
              [1, 2].map(i => <div key={i} className="h-28 bg-gray-100 animate-pulse rounded-3xl"></div>)
            ) : schemes.map((s, idx) => (
              <motion.div 
                key={s.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="glass p-6 rounded-3xl border-white/40 hover:bg-white transition-all shadow-sm border-l-4 border-l-blue-500"
              >
                <div className="flex justify-between items-start mb-3">
                  <h4 className="font-bold text-gray-900">{s.name}</h4>
                  <a href={s.link} target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-blue-600 transition">
                    <ExternalLink size={18} />
                  </a>
                </div>
                <div className="flex flex-wrap gap-2 mt-4">
                  {Object.entries(s.eligibility_criteria).map(([key, value]) => (
                    <span key={key} className="px-3 py-1 bg-gray-100 text-[10px] font-black uppercase text-gray-500 rounded-lg tracking-widest">
                       {key.replace('_', ' ')}: {value}
                    </span>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Scholarships;
