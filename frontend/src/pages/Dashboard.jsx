import React, { useState, useEffect, useContext } from 'react';
import api from '../services/api';
import { AuthContext } from '../context/AuthContext';
import { Users, UserCheck, AlertTriangle, Activity, TrendingUp, Calendar, ChevronRight, Target, BookOpen, Award } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { motion } from 'framer-motion';

const Dashboard = () => {
  const { user } = useContext(AuthContext);
  const [students, setStudents] = useState([]);
  const [atRisk, setAtRisk] = useState([]);
  const [exams, setExams] = useState([]);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const isTeacher = user?.role === 'teacher';
      const requests = [api.get('/attendance/low/?threshold=75')];
      if (isTeacher) {
        requests.push(api.get('/students/'), api.get('/exams/'), api.get('/agents/'));
      }
      const results = await Promise.allSettled(requests);
      const riskData = results[0].status === 'fulfilled' ? results[0].value.data : [];
      setAtRisk(riskData);
      if (isTeacher) {
        if (results[1].status === 'fulfilled') setStudents(results[1].value.data);
        if (results[2].status === 'fulfilled') setExams(results[2].value.data);
        if (results[3].status === 'fulfilled') setAgents(results[3].value.data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const isTeacher = user?.role === 'teacher';
  const totalStudents = students.length;
  const avgMarks = totalStudents > 0 ? (students.reduce((a, s) => a + (s.marks_12th || 0), 0) / totalStudents).toFixed(1) : 0;
  const highRisk = atRisk.filter(s => s.attendance_percentage < 65).length;
  const mediumRisk = atRisk.filter(s => s.attendance_percentage >= 65 && s.attendance_percentage < 75).length;
  const safe = totalStudents - atRisk.length;

  const chartData = [
    { name: 'Mon', attendance: 88 }, { name: 'Tue', attendance: 92 },
    { name: 'Wed', attendance: 85 }, { name: 'Thu', attendance: 90 }, { name: 'Fri', attendance: 94 },
  ];

  const teacherCards = [
    { name: 'Total Enrollment', value: totalStudents, icon: <Users />, color: 'blue', bg: 'from-blue-500 to-blue-600' },
    { name: 'High Risk Students', value: highRisk, icon: <AlertTriangle />, color: 'red', bg: 'from-red-500 to-red-600' },
    { name: 'Avg Performance', value: `${avgMarks}%`, icon: <Target />, color: 'purple', bg: 'from-purple-500 to-purple-600' },
    { name: 'Upcoming Exams', value: exams.length, icon: <Calendar />, color: 'orange', bg: 'from-orange-500 to-orange-600' },
  ];

  const studentCards = [
    { name: 'Your Attendance', value: '—', icon: <UserCheck />, color: 'blue', bg: 'from-blue-500 to-blue-600' },
    { name: 'Scholarships', value: '4', icon: <Award />, color: 'green', bg: 'from-green-500 to-green-600' },
    { name: 'Upcoming Exams', value: exams.length, icon: <Calendar />, color: 'orange', bg: 'from-orange-500 to-orange-600' },
    { name: 'Agents Available', value: '8', icon: <Activity />, color: 'purple', bg: 'from-purple-500 to-purple-600' },
  ];

  const cards = isTeacher ? teacherCards : studentCards;
  const now = new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

  return (
    <div className="p-8 space-y-8 min-h-screen">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="flex justify-between items-start">
        <div>
          <h2 className="text-3xl font-black text-gray-900 tracking-tight">
            {isTeacher ? '🏫 Teacher Dashboard' : '🎓 Student Portal'}
          </h2>
          <p className="text-gray-500 mt-1">Welcome back, <strong>{user?.full_name || user?.email}</strong> • {now}</p>
        </div>
        <div className="flex items-center space-x-2 bg-green-50 border border-green-200 px-4 py-2 rounded-2xl">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-xs font-bold text-green-700 uppercase tracking-widest">Live System</span>
        </div>
      </motion.div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
        {cards.map((card, i) => (
          <motion.div key={card.name} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
            className="glass p-6 rounded-3xl border-white/40 shadow-sm hover:scale-[1.02] transition-transform">
            <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${card.bg} flex items-center justify-center text-white shadow-lg mb-4`}>
              {React.cloneElement(card.icon, { size: 22 })}
            </div>
            <p className="text-2xl font-black text-gray-900">{loading ? '...' : card.value}</p>
            <p className="text-xs text-gray-500 font-semibold mt-1 uppercase tracking-wide">{card.name}</p>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Chart */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
          className="lg:col-span-2 glass p-8 rounded-3xl border-white/40 shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
            <TrendingUp className="text-blue-500" size={20} /> Weekly Attendance Trend
          </h3>
          <div className="h-[250px] w-full">
            <ResponsiveContainer width="100%" height="100%" minHeight={250} minWidth={200}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="attGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#9ca3af', fontWeight: 700 }} />
                <YAxis domain={[70, 100]} axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#9ca3af', fontWeight: 700 }} />
                <Tooltip contentStyle={{ borderRadius: '16px', border: 'none', boxShadow: '0 10px 25px rgba(0,0,0,0.1)' }} />
                <Area type="monotone" dataKey="attendance" stroke="#3b82f6" strokeWidth={3} fill="url(#attGrad)" dot={{ r: 4, fill: '#3b82f6' }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Risk / At-Risk Students */}
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5 }}
          className="glass p-8 rounded-3xl border-white/40 shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-6">
            {isTeacher ? '⚠️ Attendance Alerts' : '📋 Quick Actions'}
          </h3>
          {isTeacher ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center p-4 bg-red-50 rounded-2xl border border-red-100">
                <div>
                  <p className="font-bold text-red-700 text-sm">🔴 Critical ({`<`}65%)</p>
                  <p className="text-xs text-red-500">Immediate action needed</p>
                </div>
                <span className="text-2xl font-black text-red-700">{loading ? '...' : highRisk}</span>
              </div>
              <div className="flex justify-between items-center p-4 bg-yellow-50 rounded-2xl border border-yellow-100">
                <div>
                  <p className="font-bold text-yellow-700 text-sm">🟡 Warning (65–75%)</p>
                  <p className="text-xs text-yellow-500">Monitor closely</p>
                </div>
                <span className="text-2xl font-black text-yellow-700">{loading ? '...' : mediumRisk}</span>
              </div>
              <div className="flex justify-between items-center p-4 bg-green-50 rounded-2xl border border-green-100">
                <div>
                  <p className="font-bold text-green-700 text-sm">🟢 Safe ({`>`}75%)</p>
                  <p className="text-xs text-green-500">All good</p>
                </div>
                <span className="text-2xl font-black text-green-700">{loading ? '...' : Math.max(0, safe)}</span>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {[
                { label: 'Check Attendance', path: '/attendance', icon: '📋', color: 'blue' },
                { label: 'Scholarships', path: '/scholarships', icon: '🏆', color: 'green' },
                { label: 'Request Letter', path: '/letters', icon: '📄', color: 'purple' },
                { label: 'Chat with AI', path: '/chat', icon: '🤖', color: 'indigo' },
              ].map(act => (
                <a key={act.label} href={act.path}
                  className={`flex items-center justify-between p-4 bg-${act.color}-50 rounded-2xl border border-${act.color}-100 hover:bg-${act.color}-100 transition group`}>
                  <span className="font-semibold text-gray-800 text-sm">{act.icon} {act.label}</span>
                  <ChevronRight size={16} className="text-gray-400 group-hover:translate-x-1 transition-transform" />
                </a>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      {/* At-Risk Students Table (Teacher only) */}
      {isTeacher && atRisk.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}
          className="glass p-8 rounded-3xl border-white/40 shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-6">🚨 Students Requiring Immediate Attention</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs font-black uppercase tracking-widest text-gray-400 border-b border-gray-100">
                  <th className="pb-4">Student</th>
                  <th className="pb-4">Roll No</th>
                  <th className="pb-4">Dept</th>
                  <th className="pb-4">Attendance</th>
                  <th className="pb-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {atRisk.map(s => (
                  <tr key={s.roll_no} className="hover:bg-gray-50/50 transition">
                    <td className="py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-red-100 text-red-600 flex items-center justify-center font-bold text-sm">
                          {s.name?.charAt(0)}
                        </div>
                        <span className="font-semibold text-gray-900">{s.name}</span>
                      </div>
                    </td>
                    <td className="py-4 font-mono text-sm text-gray-600">{s.roll_no}</td>
                    <td className="py-4 text-sm text-gray-600">{s.department}</td>
                    <td className="py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div className="h-2 rounded-full bg-red-500" style={{ width: `${s.attendance_percentage}%` }} />
                        </div>
                        <span className="text-sm font-bold text-red-600">{s.attendance_percentage?.toFixed(1)}%</span>
                      </div>
                    </td>
                    <td className="py-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${s.attendance_percentage < 65 ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'}`}>
                        {s.attendance_percentage < 65 ? 'CRITICAL' : 'WARNING'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default Dashboard;
