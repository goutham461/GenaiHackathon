import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';
import {
  Calendar, Clock, MapPin, AlertOctagon, Bot, Send, Sparkles,
  X, Filter, Search, Plus, ShieldAlert, AlignLeft, RefreshCw,
  MoreVertical, CheckCircle2, ChevronDown, CheckSquare, Loader2
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
  'Schedule midterm exams for IT semester 4 next week',
  'What exams are scheduled tomorrow?',
  'Move Data Structures exam to next Monday',
  'Check if there are any exam conflicts',
  'Cancel the Mathematics exam',
  'Show exam timetable for CSE department',
];

const DEPARTMENTS = ['CS', 'IT', 'ECE', 'EEE', 'MECH', 'CIVIL', 'AI', 'DS'];
const SEMESTERS = [1, 2, 3, 4, 5, 6, 7, 8];

/* ─── Chat Message ─── */
const ChatMsg = ({ msg }) => (
  <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
    <div className={`max-w-[88%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
      msg.role === 'user'
        ? 'bg-gradient-to-br from-indigo-500 to-purple-500 text-white rounded-br-sm'
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
const Exams = () => {
  const [exams, setExams] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [filterDept, setFilterDept] = useState('');
  const [filterSem, setFilterSem] = useState('');
  const [search, setSearch] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // Chat
  const [chatOpen, setChatOpen] = useState(false);
  const [agentId, setAgentId] = useState(null);
  const [messages, setMessages] = useState([{
    role: 'agent',
    text: "📅 Hi! I'm the **Exam Scheduler Agent**.\n\nAsk me to:\n- *Schedule exams for semester 3 next week*\n- *Move Physics exam to Friday*\n- *Check exam conflicts in IT*\n- *Show upcoming CSE timetable*",
  }]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef(null);

  /* ─── Fetch ─── */
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterDept) params.department = filterDept;
      if (filterSem) params.semester = filterSem;
      
      const [exRes, confRes] = await Promise.all([
        api.get('/exams/', { params }),
        api.get('/exams/conflicts/', { params })
      ]);
      setExams(exRes.data);
      setConflicts(confRes.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  }, [filterDept, filterSem]);

  const fetchAgentId = async () => {
    try {
      const res = await api.get('/agents/');
      const agents = res.data.results || res.data;
      const exAgent = agents.find(a => a.domain === 'exam' || a.name?.toLowerCase().includes('exam') || a.name?.toLowerCase().includes('scheduler'));
      if (exAgent) setAgentId(exAgent.id);
      else if (agents.length) setAgentId(agents[0].id);
    } catch (e) {}
  };

  useEffect(() => { fetchAgentId(); }, []);
  useEffect(() => { fetchData(); }, [fetchData]);
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
      // Refresh board if schedule changed
      if (msg.match(/schedule|move|update|delete|cancel|change/i)) {
          setTimeout(fetchData, 1000);
      }
    } catch {
      setMessages(p => [...p, { role: 'agent', text: '⚠️ Could not reach the Exam Scheduler Agent. Please try again.' }]);
    } finally { setChatLoading(false); }
  };

  /* ─── Data Prep ─── */
  const filtered = exams.filter(e => {
    if (!search) return true;
    const q = search.toLowerCase();
    return e.course_name?.toLowerCase().includes(q) || e.course_code?.toLowerCase().includes(q);
  });

  // Group exams by Date
  const groupedExams = filtered.reduce((acc, exam) => {
      const dateStr = new Date(exam.date).toDateString();
      if (!acc[dateStr]) acc[dateStr] = [];
      acc[dateStr].push(exam);
      return acc;
  }, {});
  
  const sortedDates = Object.keys(groupedExams).sort((a, b) => new Date(a) - new Date(b));

  return (
    <div className="flex h-full min-h-screen bg-slate-50">

      {/* ══ MAIN ══ */}
      <div className={`flex-1 p-6 lg:p-8 space-y-6 transition-all duration-300 ${chatOpen ? 'mr-[420px]' : ''}`}>

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
              <Calendar className="text-indigo-600" size={32} />
              Exam Scheduler
            </h1>
            <p className="text-slate-500 mt-1 text-sm">Timetables · Conflict Detection · Room Allocation</p>
          </div>
          <div className="flex gap-3">
            <button onClick={() => setChatOpen(o => !o)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm transition shadow-sm ${
                chatOpen ? 'bg-indigo-600 text-white shadow-indigo-500/20' : 'bg-white border border-slate-200 text-slate-700 hover:border-indigo-300 hover:text-indigo-700'
              }`}>
              <Bot size={17} /> Schedule via AI
            </button>
            <button onClick={fetchData}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white border border-slate-200 text-slate-600 hover:text-indigo-600 hover:border-indigo-300 transition shadow-sm text-sm font-medium">
              <RefreshCw size={16} /> Refresh
            </button>
          </div>
        </motion.div>

        {/* Stats Dashboard */}
        <div className="grid grid-cols-3 gap-4">
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-blue-600"><Calendar size={24} /></div>
                <div>
                    <p className="text-2xl font-bold text-slate-900">{exams.length}</p>
                    <p className="text-sm font-medium text-slate-500">Scheduled Exams</p>
                </div>
            </motion.div>
            
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
                className={`bg-white rounded-2xl p-5 border shadow-sm flex items-center gap-4 ${conflicts.length > 0 ? 'border-red-200 bg-red-50/30' : 'border-slate-200'}`}>
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${conflicts.length > 0 ? 'bg-red-100 text-red-600' : 'bg-emerald-100 text-emerald-600'}`}>
                    {conflicts.length > 0 ? <AlertOctagon size={24} /> : <CheckCircle2 size={24} />}
                </div>
                <div>
                    <p className={`text-2xl font-bold ${conflicts.length > 0 ? 'text-red-700' : 'text-slate-900'}`}>{conflicts.length}</p>
                    <p className="text-sm font-medium text-slate-500">Schedule Conflicts</p>
                </div>
            </motion.div>
            
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
                className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-purple-100 flex items-center justify-center text-purple-600"><MapPin size={24} /></div>
                <div>
                    <p className="text-2xl font-bold text-slate-900">{new Set(exams.map(e => e.room).filter(Boolean)).size}</p>
                    <p className="text-sm font-medium text-slate-500">Rooms Allocated</p>
                </div>
            </motion.div>
        </div>

        {/* Conflicts Alert */}
        <AnimatePresence>
            {conflicts.length > 0 && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                    className="bg-red-50 border border-red-200 rounded-2xl overflow-hidden shadow-sm">
                    <div className="px-5 py-3 bg-red-100/50 border-b border-red-200 flex items-center gap-3">
                        <ShieldAlert className="text-red-600" size={20} />
                        <h3 className="font-bold text-red-800">Schedule Conflicts Detected ({conflicts.length})</h3>
                    </div>
                    <div className="p-5 space-y-3">
                        {conflicts.map((c, i) => (
                            <div key={i} className="flex items-center gap-4 bg-white p-3 rounded-xl border border-red-100 shadow-sm">
                                <div className="flex-1">
                                    <p className="text-sm font-bold text-slate-800">{c.exam1.course_name} <span className="text-red-500 font-normal mx-2">VS</span> {c.exam2.course_name}</p>
                                    <p className="text-xs text-slate-500 mt-1">Both scheduled on **{c.exam1.date}**</p>
                                </div>
                                <div className="px-3 py-1 bg-red-100 text-red-700 rounded-lg text-xs font-bold whitespace-nowrap">
                                    {c.reason}
                                </div>
                                <button onClick={() => setChatOpen(true)} className="px-3 py-1.5 bg-white border border-slate-200 text-slate-600 text-xs font-medium rounded-lg hover:border-indigo-300 hover:text-indigo-600 transition">
                                    Fix with AI
                                </button>
                            </div>
                        ))}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>

        {/* Filters */}
        <div className="space-y-3">
          <div className="flex gap-3">
            <div className="flex-1 bg-white flex items-center px-4 py-3 rounded-xl border border-slate-200 focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-100 transition shadow-sm">
              <Search className="text-slate-400 mr-3 flex-shrink-0" size={18} />
              <input type="text" placeholder="Search course name or code…"
                className="bg-transparent border-none outline-none w-full text-slate-700 text-sm"
                value={search} onChange={e => setSearch(e.target.value)} />
            </div>
            <button onClick={() => setShowFilters(f => !f)}
              className={`flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-medium border transition shadow-sm ${
                showFilters || filterDept || filterSem ? 'bg-indigo-50 border-indigo-200 text-indigo-700' : 'bg-white border-slate-200 text-slate-600'
              }`}>
              <Filter size={16} /> Filters
            </button>
          </div>

          <AnimatePresence>
            {showFilters && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm overflow-hidden">
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <label className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 block">Department</label>
                    <select value={filterDept} onChange={e => setFilterDept(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm outline-none focus:ring-2 focus:ring-indigo-400 bg-slate-50">
                      <option value="">All Departments</option>
                      {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 block">Semester</label>
                     <select value={filterSem} onChange={e => setFilterSem(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm outline-none focus:ring-2 focus:ring-indigo-400 bg-slate-50">
                      <option value="">All Semesters</option>
                      {SEMESTERS.map(d => <option key={d} value={d}>Semester {d}</option>)}
                    </select>
                  </div>
                </div>
                {(filterDept || filterSem) && (
                  <div className="mt-4 pt-4 border-t border-slate-100 flex justify-end">
                      <button onClick={() => { setFilterDept(''); setFilterSem(''); }} className="text-xs text-red-500 hover:text-red-700 font-medium px-3 py-1.5 rounded-lg hover:bg-red-50 transition">
                        Clear all filters
                      </button>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Timetable View */}
        <div className="space-y-8 pb-10">
            {loading ? (
                <div className="flex justify-center py-20"><Loader2 className="animate-spin text-indigo-400" size={32} /></div>
            ) : sortedDates.length === 0 ? (
                <div className="bg-white rounded-3xl border border-slate-200 p-16 text-center shadow-sm">
                    <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-slate-100">
                      <Calendar size={32} className="text-slate-400" />
                    </div>
                    <h3 className="text-xl font-bold text-slate-900">No Exams Scheduled</h3>
                    <p className="text-slate-500 mt-2 text-sm max-w-sm mx-auto">
                      There are no exams matching your current filters. Open the AI Assistant to schedule new exams.
                    </p>
                    <button onClick={() => setChatOpen(true)} className="mt-6 px-6 py-2.5 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 transition shadow-sm inline-flex items-center gap-2 text-sm">
                        <Bot size={16} /> Tell AI to Schedule Exams
                    </button>
                </div>
            ) : (
                sortedDates.map(dateStr => (
                    <div key={dateStr} className="relative">
                        <div className="flex items-center gap-4 mb-4">
                            <h2 className="text-lg font-bold text-slate-800 relative z-10 bg-slate-50 pr-4">{new Date(dateStr).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}</h2>
                            <div className="h-px bg-slate-200 flex-1 relative top-0.5"></div>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                            {groupedExams[dateStr].map(exam => (
                                <motion.div key={exam.id} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                                    className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md hover:border-indigo-200 transition-all group">
                                    <div className="flex justify-between items-start mb-3">
                                        <div className="px-2.5 py-1 bg-slate-100 text-slate-600 rounded-lg text-xs font-bold uppercase tracking-wider">
                                            {exam.exam_type}
                                        </div>
                                        <div className="flex items-center gap-1 text-slate-400">
                                            <span className="text-xs font-bold">{exam.course_code || 'CODE'}</span>
                                        </div>
                                    </div>
                                    
                                    <h3 className="font-bold text-slate-900 text-lg mb-1 group-hover:text-indigo-700 transition-colors">{exam.course_name}</h3>
                                    <div className="flex items-center gap-2 mb-4">
                                        <span className="text-xs font-medium text-slate-500 bg-slate-50 px-2 py-0.5 rounded-full border border-slate-100">{exam.department || '?'}</span>
                                        <span className="text-xs font-medium text-slate-500 bg-slate-50 px-2 py-0.5 rounded-full border border-slate-100">Sem {exam.semester || '?'}</span>
                                    </div>
                                    
                                    <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-sm">
                                        <div className="flex items-center gap-1.5 text-slate-600 font-medium">
                                            <Clock size={16} className="text-indigo-400" />
                                            {exam.start_time ? `${exam.start_time.substring(0,5)} - ${exam.end_time?.substring(0,5)}` : 'Time TBD'}
                                        </div>
                                        <div className="flex items-center gap-1.5 text-slate-600 font-medium">
                                            <MapPin size={16} className="text-teal-500" />
                                            {exam.room || 'Room TBD'}
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                ))
            )}
        </div>
      </div>

      {/* ══ AI CHAT PANEL ══ */}
      <AnimatePresence>
        {chatOpen && (
          <motion.div
            initial={{ x: 420, opacity: 0 }} animate={{ x: 0, opacity: 1 }}
            exit={{ x: 420, opacity: 0 }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 h-full w-[420px] bg-white border-l border-slate-200 flex flex-col shadow-2xl z-40">

            {/* Chat Header */}
            <div className="px-6 py-5 bg-gradient-to-r from-indigo-600 to-purple-600 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center border border-white/10 shadow-inner">
                  <Sparkles size={20} className="text-white" />
                </div>
                <div>
                  <p className="font-bold text-white">Exam Scheduler Agent</p>
                  <p className="text-indigo-100 text-xs font-medium">Automatic Scheduling & Conflicts</p>
                </div>
              </div>
              <button onClick={() => setChatOpen(false)} className="p-2 rounded-xl hover:bg-white/20 text-white transition">
                <X size={20} />
              </button>
            </div>

            {/* Quick Chips */}
            <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/80 flex-shrink-0">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Quick Commands</p>
              <div className="flex flex-wrap gap-2">
                {QUICK_CHIPS.map(chip => (
                  <button key={chip} onClick={() => sendChat(chip)}
                    className="text-xs px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-600 hover:border-indigo-300 hover:text-indigo-700 hover:bg-indigo-50 transition font-medium text-left leading-tight shadow-sm">
                    {chip}
                  </button>
                ))}
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-slate-50/50">
              {messages.map((msg, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                  <ChatMsg msg={msg} />
                </motion.div>
              ))}
              {chatLoading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-slate-100 rounded-2xl rounded-bl-sm px-5 py-3.5 shadow-sm">
                    <div className="flex items-center gap-2 text-slate-400 text-xs font-medium">
                      <Loader2 size={16} className="animate-spin text-indigo-500" /> Computing Timetable…
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input */}
            <div className="p-5 border-t border-slate-100 bg-white shadow-[0_-10px_40px_rgba(0,0,0,0.03)] flex-shrink-0">
              <div className="flex gap-2 bg-slate-50 rounded-2xl border border-slate-200 focus-within:border-indigo-400 focus-within:ring-4 focus-within:ring-indigo-50 transition-all overflow-hidden p-1 shadow-inner">
                <textarea 
                  value={chatInput} 
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          sendChat();
                      }
                  }}
                  placeholder="Tell me what exams to schedule…"
                  className="flex-1 bg-transparent px-4 py-3 outline-none text-sm text-slate-700 placeholder-slate-400 resize-none max-h-32 min-h-[44px]"
                  rows={Math.min(chatInput.split('\n').length, 3) || 1}
                  disabled={chatLoading} 
                />
                <button onClick={() => sendChat()} disabled={!chatInput.trim() || chatLoading}
                  className="self-end m-1 w-10 h-10 flex items-center justify-center bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition shadow-sm">
                  <Send size={18} className="ml-0.5" />
                </button>
              </div>
              <p className="text-center text-[10px] text-slate-400 mt-3 font-medium uppercase tracking-widest">Powered by UniAgent AI</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Exams;
