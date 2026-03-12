import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Calendar, Clock, MapPin, Award, User, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';

const Exams = () => {
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchExams();
  }, []);

  const fetchExams = async () => {
    try {
      const res = await api.get('/exams/');
      setExams(res.data);
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
        <h2 className="text-3xl font-bold text-gray-900 font-display">Exam Schedule</h2>
        <p className="text-gray-500">Upcoming midterms, finals, and room allocations.</p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-6">
          <h3 className="text-xl font-bold text-gray-900 px-2">Upcoming Assessments</h3>
          {loading ? (
             [1, 2, 3].map(i => <div key={i} className="h-32 bg-gray-100 animate-pulse rounded-3xl"></div>)
          ) : exams.map((e, idx) => (
            <motion.div
              key={e.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              className="glass p-6 rounded-3xl border-white/40 flex items-center justify-between group cursor-pointer hover:shadow-xl hover:shadow-blue-500/5 transition-all"
            >
              <div className="flex items-center space-x-6">
                <div className="text-center bg-gray-100 px-4 py-3 rounded-2xl group-hover:bg-blue-600 group-hover:text-white transition-colors">
                  <span className="block text-xs font-bold uppercase tracking-tighter opacity-70">MAR</span>
                  <span className="block text-2xl font-black">{new Date(e.date).getDate()}</span>
                </div>
                <div>
                  <h4 className="font-extrabold text-gray-900 group-hover:text-blue-600 transition-colors uppercase tracking-tight">{e.course_name}</h4>
                  <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                    <span className="flex items-center space-x-1 uppercase font-bold text-[10px]">
                      <Clock size={12} className="text-gray-400" />
                      <span>{e.exam_type}</span>
                    </span>
                    <span className="flex items-center space-x-1 uppercase font-bold text-[10px]">
                      <MapPin size={12} className="text-gray-400" />
                      <span>{e.room}</span>
                    </span>
                  </div>
                </div>
              </div>
              <div className="text-right flex flex-col items-end">
                <div className="flex items-center space-x-2 text-gray-400 group-hover:text-blue-500 transition-colors">
                  <span className="text-xs font-bold uppercase">Details</span>
                  <ChevronRight size={18} />
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="space-y-8">
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass p-8 rounded-[2.5rem] border-white/40 shadow-sm bg-gray-900 text-white overflow-hidden relative"
          >
             {/* Decorative circles */}
             <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/20 rounded-full blur-3xl -mr-20 -mt-20"></div>
             <div className="absolute bottom-0 left-0 w-48 h-48 bg-blue-500/20 rounded-full blur-3xl -ml-20 -mb-20"></div>

             <div className="relative">
                <h3 className="text-2xl font-black mb-6 italic uppercase tracking-tighter">Campus Hall of Fame</h3>
                <p className="text-gray-400 text-sm mb-8">Top performing students in last month's assessments.</p>
                
                <div className="space-y-6">
                  {[
                    { name: 'Ravi Kumar', score: 98, course: 'Data Structures' },
                    { name: 'Priya Singh', score: 96, course: 'Engineering Maths' }
                  ].map((s, idx) => (
                    <div key={idx} className="flex items-center justify-between group">
                      <div className="flex items-center space-x-4">
                        <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center font-bold text-white group-hover:bg-white/20 transition-colors">
                          {idx + 1}
                        </div>
                        <div>
                          <p className="font-bold text-white group-hover:text-blue-300 transition-colors">{s.name}</p>
                          <p className="text-[10px] text-gray-500 uppercase font-black tracking-widest leading-none mt-1">{s.course}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="text-xl font-black text-transparent bg-clip-text bg-gradient-to-tr from-blue-400 to-purple-400">{s.score}%</span>
                      </div>
                    </div>
                  ))}
                </div>

                <button className="w-full mt-10 py-4 rounded-2xl bg-white/10 hover:bg-white/20 border border-white/10 text-sm font-bold uppercase tracking-widest transition-all">
                  View Full Rankings
                </button>
             </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default Exams;
