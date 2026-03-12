import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { UserCheck, Calendar, Filter, AlertCircle, TrendingDown, TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';

const Attendance = () => {
  const [atRisk, setAtRisk] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAtRisk();
  }, []);

  const fetchAtRisk = async () => {
    try {
      const res = await api.get('/attendance/low/?threshold=75');
      setAtRisk(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-8 min-h-screen bg-gray-50/50">
      <div className="flex justify-between items-end">
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <h2 className="text-3xl font-bold text-gray-900">Attendance Monitoring</h2>
          <p className="text-gray-500">Real-time risk detection and daily attendance tracking.</p>
        </motion.div>
        
        <div className="flex space-x-3">
          <button className="glass px-5 py-2.5 rounded-xl border-white/40 flex items-center space-x-2 text-gray-600 hover:text-blue-600 transition">
            <Calendar size={18} />
            <span className="font-medium text-sm">Mark Today</span>
          </button>
          <button className="bg-blue-600 text-white px-5 py-2.5 rounded-xl shadow-lg shadow-blue-500/20 hover:bg-blue-700 transition flex items-center space-x-2">
            <Filter size={18} />
            <span className="font-medium text-sm">Export Report</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="lg:col-span-2 glass p-8 rounded-[2.5rem] border-white/40 shadow-sm"
        >
          <div className="flex items-center justify-between mb-8">
            <h3 className="text-xl font-bold text-gray-900 flex items-center space-x-2">
              <AlertCircle className="text-red-500" />
              <span>High Risk Students (&lt; 75%)</span>
            </h3>
            <span className="text-xs font-bold text-red-500 bg-red-50 px-3 py-1 rounded-full uppercase">Priority Review</span>
          </div>

          <div className="space-y-4">
            {loading ? (
              [1, 2].map(i => <div key={i} className="h-20 bg-gray-100 animate-pulse rounded-2xl"></div>)
            ) : atRisk.length > 0 ? atRisk.map((s) => (
              <div key={s.roll_no} className="flex items-center justify-between p-5 rounded-2xl hover:bg-gray-50/50 border border-transparent hover:border-gray-100 transition-all">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center font-bold">
                    {s.name.charAt(0)}
                  </div>
                  <div>
                    <h4 className="font-bold text-gray-900">{s.name}</h4>
                    <p className="text-xs text-gray-500 font-mono uppercase">{s.roll_no} • CS • Year 3</p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="flex items-center space-x-2 text-red-600 font-bold text-lg mb-1">
                    <TrendingDown size={18} />
                    <span>{s.attendance_percentage}%</span>
                  </div>
                  <p className="text-[10px] text-gray-400 uppercase font-bold tracking-widest">Attendance</p>
                </div>
              </div>
            )) : (
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
                  <UserCheck size={32} />
                </div>
                <h4 className="font-bold text-gray-900 text-lg">All systems go!</h4>
                <p className="text-gray-500 max-w-xs mx-auto">None of the students are currently below the critical 75% threshold.</p>
              </div>
            )}
          </div>
        </motion.div>

        <div className="space-y-6">
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass p-8 rounded-[2.5rem] border-white/40 shadow-sm bg-gradient-to-br from-blue-500 to-indigo-600 text-white"
          >
            <h3 className="text-lg font-bold mb-1">Daily Summary</h3>
            <p className="text-blue-100 text-sm mb-6">Thursday, March 12, 2026</p>
            
            <div className="space-y-4">
              <div className="flex justify-between items-center bg-white/10 p-4 rounded-2xl backdrop-blur-md">
                <span className="text-sm font-medium">Class Attendance</span>
                <span className="text-xl font-bold italic">92%</span>
              </div>
              <div className="flex justify-between items-center bg-white/10 p-4 rounded-2xl backdrop-blur-md">
                <span className="text-sm font-medium">On-Time Arrival</span>
                <span className="text-xl font-bold italic">88%</span>
              </div>
              <div className="flex justify-between items-center bg-white/10 p-4 rounded-2xl backdrop-blur-md">
                <span className="text-sm font-medium">Leaves Today</span>
                <span className="text-xl font-bold italic">14</span>
              </div>
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="glass p-8 rounded-[2.5rem] border-white/40 shadow-sm"
          >
            <h3 className="text-lg font-bold text-gray-900 mb-4">Risk Trends</h3>
            <div className="flex items-center space-x-2 text-green-600 font-bold mb-2">
              <TrendingUp size={20} />
              <span className="text-2xl">-4.2%</span>
            </div>
            <p className="text-xs text-gray-400 font-medium leading-relaxed">System prediction: Overall risk is trending down as student engagement increases before midterms.</p>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default Attendance;
