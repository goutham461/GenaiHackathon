import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { GraduationCap, Briefcase, Mail, Phone, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';

const Faculty = () => {
  const [faculty, setFaculty] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFaculty();
  }, []);

  const fetchFaculty = async () => {
    try {
      const res = await api.get('/faculty/');
      setFaculty(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-8 min-h-screen bg-gray-50/50">
      <motion.div 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
      >
        <h2 className="text-3xl font-bold text-gray-900 font-display">Faculty Directory</h2>
        <p className="text-gray-500">Manage professor assignments, department workload, and contact info.</p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          [1, 2, 3].map(i => (
            <div key={i} className="glass h-64 animate-pulse rounded-3xl border-white/40"></div>
          ))
        ) : faculty.map((f, idx) => (
          <motion.div
            key={f.id}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: idx * 0.1 }}
            className="glass p-6 rounded-3xl border-white/40 relative group overflow-hidden"
          >
            {/* Background design element */}
            <div className="absolute -top-10 -right-10 w-24 h-24 bg-blue-500/10 rounded-full blur-2xl group-hover:bg-blue-500/20 transition-colors"></div>
            
            <div className="flex items-start justify-between mb-4">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-2xl font-bold">
                {f.name.charAt(0)}
              </div>
              <span className="px-3 py-1 rounded-full bg-blue-50 text-blue-600 text-[10px] font-bold uppercase tracking-wider">
                {f.department}
              </span>
            </div>

            <h3 className="text-xl font-bold text-gray-900 mb-1">{f.name}</h3>
            <p className="text-sm text-gray-500 mb-4 font-medium uppercase tracking-tight">Department of {f.department}</p>

            <div className="space-y-2.5 mb-6">
              <div className="flex items-center text-gray-600 space-x-2 text-sm">
                <Mail size={16} className="text-gray-400" />
                <span>{f.email}</span>
              </div>
              <div className="flex items-center text-gray-600 space-x-2 text-sm">
                <Phone size={16} className="text-gray-400" />
                <span>{f.phone || '+91 98765 43210'}</span>
              </div>
              <div className="flex items-center text-gray-600 space-x-2 text-sm">
                <Briefcase size={16} className="text-gray-400" />
                <span>3 Active Courses</span>
              </div>
            </div>

            <button className="w-full flex items-center justify-center space-x-2 py-3 rounded-xl bg-white/50 border border-white/40 hover:bg-white text-blue-600 font-semibold transition-all">
              <span>View Full Profile</span>
              <ChevronRight size={16} />
            </button>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default Faculty;
