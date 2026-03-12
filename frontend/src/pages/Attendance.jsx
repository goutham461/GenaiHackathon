import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';
import {
  AlertTriangle, CheckCircle, TrendingDown, TrendingUp, Bot,
  Send, Sparkles, X, Search, Filter, RefreshCw,
  Users, BarChart2, Calendar, Shield, Loader2, ChevronDown,
  AlertCircle, Activity, Clock,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

/* ─── Markdown renderer ─── */
const renderMd = (text) => {
  if (!text) return '';
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code style="background:#f1f5f9;padding:1px 6px;border-radius:4px;font-size:0.85em">$1</code>')
    .replace(/\n- /g, '\n• ')
    .replace(/\n/g, '<br/>');
};

const QUICK_CHIPS = [
  'Show students below 75% attendance',
  'Who has critical attendance (below 65%)?',
  'Which students may fall below 75% soon?',
  'Send warning emails to students below 75%',
  'How many classes must Rahul attend to reach 75?',
  'Average attendance of IT department',
  'Which department has worst attendance?',
];

/* ─── Status Badge ─── */
const StatusBadge = ({ status }) => {
  const map = {
    CRITICAL: 'bg-red-100 text-red-700 border-red-200',
    WARNING: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    SAFE: 'bg-green-100 text-green-700 border-green-200',
  };
  const icons = { CRITICAL: '🔴', WARNING: '🟡', SAFE: '🟢' };
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold border ${map[status] || map.SAFE}`}>
      {icons[status] || '🟢'} {status}
    </span>
  );
};

/* ─── Attendance Bar ─── */
const AttendanceBar = ({ pct }) => {
  const p = parseFloat(pct) || 0;
  const color = p < 65 ? 'bg-red-500' : p < 75 ? 'bg-yellow-400' : 'bg-green-500';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${Math.min(p, 100)}%` }} />
      </div>
      <span className={`text-sm font-bold w-12 text-right ${p < 65 ? 'text-red-600' : p < 75 ? 'text-yellow-600' : 'text-green-600'}`}>{p}%</span>
    </div>
  );
};

/* ─── Stat Card ─── */
const StatCard = ({ icon: Icon, label, value, color, sub, border }) => (
  <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
    className={`bg-white rounded-2xl p-5 border shadow-sm ${border || 'border-gray-100'}`}>
    <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${color}`}>
      <Icon size={19} className="text-white" />
    </div>
    <p className="text-2xl font-bold text-gray-900">{value ?? '—'}</p>
    <p className="text-sm font-medium text-gray-500 mt-0.5">{label}</p>
    {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
  </motion.div>
);

/* ─── Chat Message ─── */
const ChatMsg = ({ msg }) => (
  <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
    <div className={`max-w-[88%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
      msg.role === 'user'
        ? 'bg-gradient-to-br from-orange-500 to-red-500 text-white rounded-br-sm'
        : 'bg-white border border-gray-100 text-gray-800 rounded-bl-sm shadow-sm'
    }`}>
      {msg.role === 'agent'
        ? <span dangerouslySetInnerHTML={{ __html: renderMd(msg.text) }} />
        : msg.text}
    </div>
  </div>
);

/* ═══════════════════════════════════════════════════════
   MAIN COMPONENT
═══════════════════════════════════════════════════════ */
const Attendance = () => {
  const [atRisk, setAtRisk] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);

  // Filters
  const [threshold, setThreshold] = useState(75);
  const [filterDept, setFilterDept] = useState('');
  const [search, setSearch] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // Chat
  const [chatOpen, setChatOpen] = useState(false);
  const [agentId, setAgentId] = useState(null);
  const [messages, setMessages] = useState([{
    role: 'agent',
    text: "⚠️ Hi! I'm the **Attendance Warning Agent**.\n\nAsk me anything about student attendance:\n- *Show students below 75%*\n- *Who has critical attendance?*\n- *How many classes must Rahul attend to reach 75%?*\n- *CS department attendance average*",
  }]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef(null);

  const DEPARTMENTS = ['CS', 'IT', 'ECE', 'EEE', 'MECH', 'CIVIL', 'AI', 'DS'];

  /* ─── Fetch ─── */
  const fetchAtRisk = useCallback(async () => {
    setLoading(true);
    try {
      const params = { threshold };
      if (filterDept) params.department = filterDept;
      const res = await api.get('/attendance/low/', { params });
      setAtRisk(res.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  }, [threshold, filterDept]);

  const fetchStats = async () => {
    try {
      const res = await api.get('/attendance/stats/');
      setStats(res.data);
    } catch (err) { console.error(err); }
    finally { setStatsLoading(false); }
  };

  const fetchAgentId = async () => {
    try {
      const res = await api.get('/agents/');
      const agents = res.data.results || res.data;
      const warn = agents.find(a => a.domain === 'warning' || a.name?.toLowerCase().includes('warning') || a.name?.toLowerCase().includes('attendance'));
      if (warn) setAgentId(warn.id);
      else if (agents.length) setAgentId(agents[0].id);
    } catch (e) {}
  };

  useEffect(() => { fetchStats(); fetchAgentId(); }, []);
  useEffect(() => { fetchAtRisk(); }, [fetchAtRisk]);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  /* ─── Chat ─── */
  const sendChat = async (txt) => {
    const msg = txt || chatInput.trim();
    if (!msg) return;
    setChatInput('');
    setMessages(p => [...p, { role: 'user', text: msg }]);
    setChatLoading(true);
    try {
      if (!agentId) throw new Error('No agent');
      const res = await api.post(`/agents/${agentId}/chat/`, { message: msg });
      setMessages(p => [...p, { role: 'agent', text: res.data.response }]);
    } catch {
      setMessages(p => [...p, { role: 'agent', text: '⚠️ Could not reach the Attendance Agent. Please try again.' }]);
    } finally { setChatLoading(false); }
  };

  /* ─── Filtered list ─── */
  const filtered = atRisk.filter(s => {
    if (!search) return true;
    return s.name?.toLowerCase().includes(search.toLowerCase()) || s.roll_no?.toLowerCase().includes(search.toLowerCase());
  });

  const critical = filtered.filter(s => s.attendance_percentage < 65);
  const warning = filtered.filter(s => s.attendance_percentage >= 65 && s.attendance_percentage < 75);

  return (
    <div className="flex h-full min-h-screen bg-gray-50/50">

      {/* ══ MAIN ══ */}
      <div className={`flex-1 p-6 lg:p-8 space-y-6 transition-all duration-300 ${chatOpen ? 'mr-[400px]' : ''}`}>

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
              <AlertTriangle className="text-orange-500" size={32} />
              Attendance Monitoring
            </h1>
            <p className="text-gray-500 mt-1 text-sm">Real-time risk detection · Warning system · Department analytics</p>
          </div>
          <div className="flex gap-3">
            <button onClick={() => setChatOpen(o => !o)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm transition shadow-sm ${
                chatOpen ? 'bg-orange-500 text-white shadow-orange-500/20' : 'bg-white border border-gray-200 text-gray-700 hover:border-orange-300 hover:text-orange-600'
              }`}>
              <Bot size={17} /> AI Assistant
            </button>
            <button onClick={() => { fetchAtRisk(); fetchStats(); }}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white border border-gray-200 text-gray-600 hover:text-orange-600 hover:border-orange-300 transition shadow-sm text-sm font-medium">
              <RefreshCw size={16} /> Refresh
            </button>
          </div>
        </motion.div>

        {/* Stats Dashboard */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {statsLoading ? [1,2,3,4].map(i => <div key={i} className="h-28 bg-white rounded-2xl border border-gray-100 animate-pulse" />) : (
            <>
              <StatCard icon={Users} label="Total Students" value={stats?.total} color="bg-blue-500" />
              <StatCard icon={Activity} label="Avg Attendance" value={stats?.avg_pct ? `${stats.avg_pct}%` : '—'} color="bg-teal-500"
                sub={`${stats?.tracked} tracked`} />
              <StatCard icon={AlertTriangle} label="Warning (< 75%)" value={stats?.warning}
                color="bg-yellow-500" border="border-yellow-100"
                sub={`${stats?.critical || 0} critical`} />
              <StatCard icon={Shield} label="Critical (< 65%)" value={stats?.critical}
                color="bg-red-500" border="border-red-100"
                sub="Exam debarment risk" />
            </>
          )}
        </div>

        {/* Department Breakdown */}
        {stats?.dept_breakdown?.length > 0 && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
            <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
              <BarChart2 size={18} className="text-orange-500" />
              Department Attendance Overview
            </h3>
            <div className="space-y-3">
              {stats.dept_breakdown.map(dept => (
                <div key={dept.department} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-700 w-12">{dept.department}</span>
                      {dept.critical > 0 && (
                        <span className="text-xs text-red-600 font-bold bg-red-50 px-1.5 py-0.5 rounded-full">{dept.critical} critical</span>
                      )}
                      {dept.warning > 0 && (
                        <span className="text-xs text-yellow-600 font-bold bg-yellow-50 px-1.5 py-0.5 rounded-full">{dept.warning} warning</span>
                      )}
                    </div>
                    <span className="text-xs text-gray-400">{dept.count} students</span>
                  </div>
                  <AttendanceBar pct={dept.avg_pct} />
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Filters */}
        <div className="space-y-3">
          <div className="flex gap-3">
            <div className="flex-1 bg-white flex items-center px-4 py-2.5 rounded-xl border border-gray-200 focus-within:border-orange-400 focus-within:ring-2 focus-within:ring-orange-100 transition shadow-sm">
              <Search className="text-gray-400 mr-3 flex-shrink-0" size={16} />
              <input type="text" placeholder="Search student name or roll no…"
                className="bg-transparent border-none outline-none w-full text-gray-700 text-sm"
                value={search} onChange={e => setSearch(e.target.value)} />
            </div>
            <button onClick={() => setShowFilters(f => !f)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium border transition shadow-sm ${
                showFilters || filterDept ? 'bg-orange-50 border-orange-300 text-orange-700' : 'bg-white border-gray-200 text-gray-600'
              }`}>
              <Filter size={15} /> Filters
            </button>
          </div>

          <AnimatePresence>
            {showFilters && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm overflow-hidden">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 block">Department</label>
                    <select value={filterDept} onChange={e => setFilterDept(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm outline-none focus:ring-2 focus:ring-orange-400">
                      <option value="">All Departments</option>
                      {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 block">
                      Threshold: &lt; {threshold}%
                    </label>
                    <input type="range" min="50" max="90" step="5" value={threshold}
                      onChange={e => setThreshold(Number(e.target.value))}
                      className="w-full accent-orange-500" />
                    <div className="flex justify-between text-xs text-gray-400 mt-1">
                      <span>50%</span><span>75%</span><span>90%</span>
                    </div>
                  </div>
                </div>
                {filterDept && (
                  <button onClick={() => setFilterDept('')} className="mt-2 text-xs text-red-400 hover:text-red-600 flex items-center gap-1">
                    <X size={12} /> Clear department filter
                  </button>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Warning Tables */}
        <div className="space-y-6">

          {/* Critical */}
          {critical.length > 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="bg-white rounded-2xl border border-red-100 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-red-100 bg-red-50/60 flex items-center gap-2">
                <AlertCircle size={18} className="text-red-600" />
                <h3 className="font-bold text-red-800 text-sm">🔴 Critical Risk — Below 65% ({critical.length} students)</h3>
                <span className="ml-auto text-xs bg-red-600 text-white px-2 py-0.5 rounded-full font-bold">DEBARMENT RISK</span>
              </div>
              <table className="w-full text-left">
                <thead className="bg-red-50/40 border-b border-red-100">
                  <tr>
                    {['Student', 'Roll No', 'Dept', 'Attendance', 'Classes Needed', 'Status'].map(h => (
                      <th key={h} className="px-5 py-3 text-xs font-semibold text-red-700 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-red-50">
                  {critical.map((s, idx) => (
                    <motion.tr key={s.roll_no} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.04 }}
                      className="hover:bg-red-50/40 transition-colors">
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-red-100 text-red-700 flex items-center justify-center font-bold text-sm">
                            {s.name?.charAt(0)}
                          </div>
                          <span className="font-semibold text-gray-900 text-sm">{s.name}</span>
                        </div>
                      </td>
                      <td className="px-5 py-4 font-mono text-xs text-gray-600 font-bold">{s.roll_no}</td>
                      <td className="px-5 py-4">
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded-full text-xs font-bold">{s.department || '—'}</span>
                      </td>
                      <td className="px-5 py-4 min-w-[160px]">
                        <AttendanceBar pct={s.attendance_percentage} />
                        <p className="text-xs text-gray-400 mt-1">{s.present_days}/{s.total_days} days</p>
                      </td>
                      <td className="px-5 py-4">
                        <span className="font-bold text-red-700 text-sm">{s.classes_needed} classes</span>
                        <p className="text-xs text-gray-400">to reach 75%</p>
                      </td>
                      <td className="px-5 py-4"><StatusBadge status="CRITICAL" /></td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </motion.div>
          )}

          {/* Warning */}
          {warning.length > 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="bg-white rounded-2xl border border-yellow-100 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-yellow-100 bg-yellow-50/60 flex items-center gap-2">
                <AlertTriangle size={18} className="text-yellow-600" />
                <h3 className="font-bold text-yellow-800 text-sm">🟡 Warning — 65%–74% ({warning.length} students)</h3>
                <span className="ml-auto text-xs bg-yellow-500 text-white px-2 py-0.5 rounded-full font-bold">ATTENTION NEEDED</span>
              </div>
              <table className="w-full text-left">
                <thead className="bg-yellow-50/40 border-b border-yellow-100">
                  <tr>
                    {['Student', 'Roll No', 'Dept', 'Attendance', 'Classes Needed', 'Status'].map(h => (
                      <th key={h} className="px-5 py-3 text-xs font-semibold text-yellow-700 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-yellow-50">
                  {warning.map((s, idx) => (
                    <motion.tr key={s.roll_no} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.04 }}
                      className="hover:bg-yellow-50/40 transition-colors">
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-yellow-100 text-yellow-700 flex items-center justify-center font-bold text-sm">
                            {s.name?.charAt(0)}
                          </div>
                          <span className="font-semibold text-gray-900 text-sm">{s.name}</span>
                        </div>
                      </td>
                      <td className="px-5 py-4 font-mono text-xs text-gray-600 font-bold">{s.roll_no}</td>
                      <td className="px-5 py-4">
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded-full text-xs font-bold">{s.department || '—'}</span>
                      </td>
                      <td className="px-5 py-4 min-w-[160px]">
                        <AttendanceBar pct={s.attendance_percentage} />
                        <p className="text-xs text-gray-400 mt-1">{s.present_days}/{s.total_days} days</p>
                      </td>
                      <td className="px-5 py-4">
                        <span className="font-bold text-yellow-700 text-sm">{s.classes_needed} classes</span>
                        <p className="text-xs text-gray-400">to reach 75%</p>
                      </td>
                      <td className="px-5 py-4"><StatusBadge status="WARNING" /></td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </motion.div>
          )}

          {/* All safe */}
          {!loading && filtered.length === 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="bg-white rounded-2xl border border-green-100 p-12 text-center shadow-sm">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle size={32} className="text-green-500" />
              </div>
              <h3 className="text-xl font-bold text-gray-900">All Clear! ✅</h3>
              <p className="text-gray-500 mt-2 text-sm">
                {filterDept ? `No students in ${filterDept}` : 'No students'} are below {threshold}% attendance.
              </p>
            </motion.div>
          )}

          {loading && (
            <div className="space-y-3">
              {[1,2,3].map(i => <div key={i} className="h-20 bg-white rounded-2xl border border-gray-100 animate-pulse" />)}
            </div>
          )}
        </div>
      </div>

      {/* ══ AI CHAT PANEL ══ */}
      <AnimatePresence>
        {chatOpen && (
          <motion.div
            initial={{ x: 400, opacity: 0 }} animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 h-full w-[400px] bg-white border-l border-gray-200 flex flex-col shadow-2xl z-40">

            {/* Chat Header */}
            <div className="px-5 py-4 bg-gradient-to-r from-orange-500 to-red-500 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-white/20 flex items-center justify-center">
                  <Sparkles size={18} className="text-white" />
                </div>
                <div>
                  <p className="font-bold text-white text-sm">Attendance Warning Agent</p>
                  <p className="text-orange-100 text-xs">Natural language attendance queries</p>
                </div>
              </div>
              <button onClick={() => setChatOpen(false)} className="p-1.5 rounded-lg hover:bg-white/20 text-white transition">
                <X size={18} />
              </button>
            </div>

            {/* Quick Chips */}
            <div className="px-4 py-3 border-b border-gray-100 bg-gray-50 flex-shrink-0">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Quick Queries</p>
              <div className="flex flex-wrap gap-1.5">
                {QUICK_CHIPS.map(chip => (
                  <button key={chip} onClick={() => sendChat(chip)}
                    className="text-xs px-2.5 py-1 rounded-full bg-white border border-gray-200 text-gray-600 hover:border-orange-300 hover:text-orange-600 hover:bg-orange-50 transition whitespace-nowrap font-medium">
                    {chip}
                  </button>
                ))}
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map((msg, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                  <ChatMsg msg={msg} />
                </motion.div>
              ))}
              {chatLoading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                    <div className="flex items-center gap-2 text-gray-400 text-xs">
                      <Loader2 size={14} className="animate-spin" /> Agent thinking…
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input */}
            <div className="px-4 py-4 border-t border-gray-100 flex-shrink-0">
              <div className="flex gap-2 bg-gray-50 rounded-xl border border-gray-200 focus-within:border-orange-400 focus-within:ring-2 focus-within:ring-orange-100 transition overflow-hidden">
                <input type="text" value={chatInput} onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendChat()}
                  placeholder="Ask the Attendance Agent…"
                  className="flex-1 bg-transparent px-4 py-3 outline-none text-sm text-gray-700 placeholder-gray-400"
                  disabled={chatLoading} />
                <button onClick={() => sendChat()} disabled={!chatInput.trim() || chatLoading}
                  className="m-1.5 px-3 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-40 disabled:cursor-not-allowed transition">
                  <Send size={15} />
                </button>
              </div>
              <p className="text-center text-xs text-gray-400 mt-2">Powered by UniAgent AI</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Attendance;
