import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';
import {
  Users, Search, Plus, Trash2, Edit2, Filter, X,
  Bot, Send, GraduationCap, BarChart2, TrendingUp,
  ChevronDown, Sparkles, BookOpen, Award, Calendar,
  RefreshCw, CheckCircle, AlertCircle, Loader2,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

/* ─── Markdown-lite renderer ─── */
const renderMarkdown = (text) => {
  if (!text) return '';
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/\n- /g, '\n• ')
    .replace(/\n/g, '<br/>');
};

const DEPARTMENTS = ['CS', 'IT', 'ECE', 'EEE', 'MECH', 'CIVIL', 'AI', 'DS'];

const QUICK_CHIPS = [
  'Show all CS students',
  'Students with GPA above 8',
  'Show 2024 batch students',
  'How many students are in IT?',
  'Top 10 students by GPA',
  'Show final year students',
  'Average GPA of CSE department',
  'Department distribution',
];

const EMPTY_FORM = {
  name: '', roll_no: '', department: 'CS',
  year: 1, email: '', phone: '', gpa: '', join_year: '',
};

/* ═══════════════════════════════════════════════════════
   STAT CARD
═══════════════════════════════════════════════════════ */
const StatCard = ({ icon: Icon, label, value, color, sub }) => (
  <motion.div
    initial={{ opacity: 0, y: 16 }}
    animate={{ opacity: 1, y: 0 }}
    className={`relative overflow-hidden rounded-2xl p-5 bg-white border border-gray-100 shadow-sm`}
  >
    <div className={`w-11 h-11 rounded-xl flex items-center justify-center mb-3 ${color}`}>
      <Icon size={20} className="text-white" />
    </div>
    <p className="text-2xl font-bold text-gray-900">{value}</p>
    <p className="text-sm font-medium text-gray-500 mt-0.5">{label}</p>
    {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
  </motion.div>
);

/* ═══════════════════════════════════════════════════════
   CHAT MESSAGE
═══════════════════════════════════════════════════════ */
const ChatMessage = ({ msg }) => (
  <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
    <div className={`max-w-[88%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
      msg.role === 'user'
        ? 'bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-br-sm'
        : 'bg-white border border-gray-100 text-gray-800 rounded-bl-sm shadow-sm'
    }`}>
      {msg.role === 'agent' ? (
        <span dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.text) }} />
      ) : msg.text}
    </div>
  </div>
);

/* ═══════════════════════════════════════════════════════
   STUDENT FORM (shared Add / Edit)
═══════════════════════════════════════════════════════ */
const StudentForm = ({ formData, setFormData, onSubmit, onCancel, title, submitLabel }) => (
  <form onSubmit={onSubmit} className="space-y-4">
    <div className="grid grid-cols-2 gap-4">
      <div className="col-span-2">
        <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">Full Name</label>
        <input type="text" required placeholder="e.g. Arjun Kumar"
          className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm transition"
          value={formData.name}
          onChange={e => setFormData({ ...formData, name: e.target.value })} />
      </div>
      <div>
        <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">Roll No</label>
        <input type="text" required placeholder="e.g. CS1001"
          className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm transition font-mono"
          value={formData.roll_no}
          onChange={e => setFormData({ ...formData, roll_no: e.target.value.toUpperCase() })} />
      </div>
      <div>
        <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">Department</label>
        <select
          className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm transition"
          value={formData.department}
          onChange={e => setFormData({ ...formData, department: e.target.value })}>
          {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
        </select>
      </div>
      <div>
        <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">Academic Year</label>
        <select
          className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm transition"
          value={formData.year}
          onChange={e => setFormData({ ...formData, year: parseInt(e.target.value) })}>
          {[1,2,3,4].map(y => <option key={y} value={y}>{y}{'st nd rd th'.split(' ')[y-1]} Year</option>)}
        </select>
      </div>
      <div>
        <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">GPA</label>
        <input type="number" min="0" max="10" step="0.01" placeholder="e.g. 8.75"
          className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm transition"
          value={formData.gpa}
          onChange={e => setFormData({ ...formData, gpa: e.target.value })} />
      </div>
      <div>
        <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">Join Year</label>
        <input type="number" min="2015" max="2030" placeholder="e.g. 2024"
          className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm transition"
          value={formData.join_year}
          onChange={e => setFormData({ ...formData, join_year: e.target.value })} />
      </div>
      <div className="col-span-2">
        <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">Email</label>
        <input type="email" placeholder="student@university.edu"
          className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm transition"
          value={formData.email}
          onChange={e => setFormData({ ...formData, email: e.target.value })} />
      </div>
      <div className="col-span-2">
        <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">Phone</label>
        <input type="tel" placeholder="10-digit number"
          className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm transition"
          value={formData.phone}
          onChange={e => setFormData({ ...formData, phone: e.target.value })} />
      </div>
    </div>
    <div className="pt-2 flex space-x-3">
      <button type="button" onClick={onCancel}
        className="flex-1 py-2.5 font-semibold text-gray-600 hover:bg-gray-100 rounded-xl transition text-sm">
        Cancel
      </button>
      <button type="submit"
        className="flex-1 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-blue-800 transition shadow-lg shadow-blue-500/20 text-sm">
        {submitLabel}
      </button>
    </div>
  </form>
);

/* ═══════════════════════════════════════════════════════
   DEPARTMENT BADGE COLORS
═══════════════════════════════════════════════════════ */
const DEPT_COLORS = {
  CS: 'bg-blue-100 text-blue-700',
  IT: 'bg-violet-100 text-violet-700',
  ECE: 'bg-orange-100 text-orange-700',
  EEE: 'bg-yellow-100 text-yellow-700',
  MECH: 'bg-red-100 text-red-700',
  CIVIL: 'bg-teal-100 text-teal-700',
  AI: 'bg-pink-100 text-pink-700',
  DS: 'bg-green-100 text-green-700',
};

/* ═══════════════════════════════════════════════════════
   GPA BADGE
═══════════════════════════════════════════════════════ */
const GpaBadge = ({ gpa }) => {
  if (!gpa) return <span className="text-gray-400 text-xs">—</span>;
  const g = parseFloat(gpa);
  const cls = g >= 9 ? 'text-green-700 bg-green-100' :
              g >= 7.5 ? 'text-blue-700 bg-blue-100' :
              g >= 6 ? 'text-yellow-700 bg-yellow-100' : 'text-red-700 bg-red-100';
  return <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${cls}`}>{g.toFixed(2)}</span>;
};

/* ═══════════════════════════════════════════════════════
   MAIN PAGE
═══════════════════════════════════════════════════════ */
const Students = () => {
  const [students, setStudents] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterDept, setFilterDept] = useState('');
  const [filterYear, setFilterYear] = useState('');
  const [filterGpaGte, setFilterGpaGte] = useState('');
  const [filterJoinYear, setFilterJoinYear] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // Modals
  const [editingStudent, setEditingStudent] = useState(null);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [toastMsg, setToastMsg] = useState(null);

  // AI Chat
  const [chatOpen, setChatOpen] = useState(false);
  const [agentId, setAgentId] = useState(null);
  const [messages, setMessages] = useState([
    {
      role: 'agent',
      text: "🎓 Hi! I'm the **Student Management Agent**.\n\nAsk me anything about student data:\n- *Show CSE students with GPA above 8*\n- *Enroll student Ravi in IT, Roll No IT1099*\n- *How many students are in IT?*\n- *Top 10 students by GPA*",
    }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef(null);

  /* ── Toast ── */
  const showToast = (text, type = 'success') => {
    setToastMsg({ text, type });
    setTimeout(() => setToastMsg(null), 3500);
  };

  /* ── Fetch students with filters ── */
  const fetchStudents = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterDept) params.department = filterDept;
      if (filterYear) params.year = filterYear;
      if (filterGpaGte) params.gpa_gte = filterGpaGte;
      if (filterJoinYear) params.join_year = filterJoinYear;
      if (search) params.search = search;
      const res = await api.get('/students/', { params });
      setStudents(res.data.results || res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [filterDept, filterYear, filterGpaGte, filterJoinYear, search]);

  /* ── Fetch stats ── */
  const fetchStats = async () => {
    try {
      const res = await api.get('/students/stats/');
      setStats(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setStatsLoading(false);
    }
  };

  /* ── Fetch agent id for chat ── */
  const fetchAgentId = async () => {
    try {
      const res = await api.get('/agents/');
      const agents = res.data.results || res.data;
      const studentAgent = agents.find(a =>
        a.domain === 'student' || a.name?.toLowerCase().includes('student')
      );
      if (studentAgent) setAgentId(studentAgent.id);
      else if (agents.length > 0) setAgentId(agents[0].id);
    } catch (err) { /* no agent – chat will fail gracefully */ }
  };

  useEffect(() => {
    fetchStudents();
    fetchStats();
    fetchAgentId();
  }, []);

  useEffect(() => {
    fetchStudents();
  }, [fetchStudents]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  /* ── CRUD Handlers ── */
  const handleEnroll = async (e) => {
    e.preventDefault();
    try {
      await api.post('/students/', formData);
      setIsAddOpen(false);
      setFormData(EMPTY_FORM);
      fetchStudents();
      fetchStats();
      showToast('Student enrolled successfully! 🎉');
    } catch (err) {
      showToast('Enrollment failed. Roll No may already exist.', 'error');
    }
  };

  const handleEdit = (student) => {
    setEditingStudent(student);
    setFormData({
      name: student.name || '',
      roll_no: student.roll_no || '',
      department: student.department || 'CS',
      year: student.year || 1,
      email: student.email || '',
      phone: student.phone || '',
      gpa: student.gpa || '',
      join_year: student.join_year || '',
    });
    setIsEditOpen(true);
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    try {
      await api.patch(`/students/${editingStudent.roll_no}/`, formData);
      setIsEditOpen(false);
      fetchStudents();
      fetchStats();
      showToast('Student updated successfully! ✏️');
    } catch (err) {
      showToast('Update failed.', 'error');
    }
  };

  const handleDelete = async (roll_no, name) => {
    if (!window.confirm(`Delete ${name} (${roll_no})? This cannot be undone.`)) return;
    try {
      await api.delete(`/students/${roll_no}/`);
      fetchStudents();
      fetchStats();
      showToast(`${name} deleted successfully.`);
    } catch (err) {
      showToast('Delete failed.', 'error');
    }
  };

  /* ── AI Chat ── */
  const sendChat = async (text) => {
    const userMsg = text || chatInput.trim();
    if (!userMsg) return;
    setChatInput('');
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setChatLoading(true);
    try {
      if (!agentId) throw new Error('No agent found');
      const res = await api.post(`/agents/${agentId}/chat/`, { message: userMsg });
      setMessages(prev => [...prev, { role: 'agent', text: res.data.response }]);
      // Refresh if a CRUD operation likely happened
      if (/enroll|delete|update|change|modify/i.test(userMsg)) {
        fetchStudents();
        fetchStats();
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: 'agent', text: '⚠️ Could not reach the Student Agent. Please try again.' }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const clearFilters = () => {
    setFilterDept('');
    setFilterYear('');
    setFilterGpaGte('');
    setFilterJoinYear('');
    setSearch('');
  };

  const hasFilters = filterDept || filterYear || filterGpaGte || filterJoinYear || search;

  return (
    <div className="flex h-full min-h-screen bg-gray-50/50">
      {/* Main Content */}
      <div className={`flex-1 p-6 lg:p-8 space-y-6 transition-all duration-300 ${chatOpen ? 'mr-[400px]' : ''}`}>

        {/* ══ HEADER ══ */}
        <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
              <GraduationCap className="text-blue-600" size={32} />
              Student Management
            </h1>
            <p className="text-gray-500 mt-1 text-sm">Enroll, manage, and analyze student data with AI assistance.</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setChatOpen(o => !o)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm transition shadow-sm ${
                chatOpen
                  ? 'bg-blue-600 text-white shadow-blue-500/20'
                  : 'bg-white border border-gray-200 text-gray-700 hover:border-blue-300 hover:text-blue-600'
              }`}
            >
              <Bot size={17} />
              AI Assistant
            </button>
            <button
              onClick={() => { setFormData(EMPTY_FORM); setIsAddOpen(true); }}
              className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white px-4 py-2.5 rounded-xl hover:from-blue-700 hover:to-blue-800 transition shadow-lg shadow-blue-500/20 font-semibold text-sm"
            >
              <Plus size={17} />
              Enroll Student
            </button>
          </div>
        </motion.div>

        {/* ══ STATS DASHBOARD ══ */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {statsLoading ? (
            [1,2,3,4].map(i => (
              <div key={i} className="rounded-2xl bg-white border border-gray-100 p-5 animate-pulse h-28" />
            ))
          ) : (
            <>
              <StatCard icon={Users} label="Total Students" value={stats?.total ?? '—'}
                color="bg-blue-500" sub={`${stats?.new_this_year ?? 0} new this year`} />
              <StatCard icon={Award} label="Average GPA" value={stats?.avg_gpa ? stats.avg_gpa.toFixed(2) : '—'}
                color="bg-violet-500" />
              <StatCard icon={BookOpen} label="Departments"
                value={stats?.dept_breakdown?.length ?? '—'}
                color="bg-orange-500"
                sub={stats?.dept_breakdown?.[0] ? `Most: ${stats.dept_breakdown[0].department} (${stats.dept_breakdown[0].count})` : undefined} />
              <StatCard icon={Calendar} label="New This Year" value={stats?.new_this_year ?? '—'}
                color="bg-green-500" sub="Current join year" />
            </>
          )}
        </div>

        {/* ══ SEARCH & FILTERS ══ */}
        <div className="space-y-3">
          <div className="flex gap-3">
            <div className="flex-1 bg-white flex items-center px-4 py-2.5 rounded-xl border border-gray-200 focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-100 transition shadow-sm">
              <Search className="text-gray-400 mr-3 flex-shrink-0" size={17} />
              <input
                type="text"
                placeholder="Search by name, roll no or email…"
                className="bg-transparent border-none outline-none w-full text-gray-700 text-sm"
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
              {search && (
                <button onClick={() => setSearch('')} className="text-gray-400 hover:text-gray-600 ml-2">
                  <X size={15} />
                </button>
              )}
            </div>
            <button
              onClick={() => setShowFilters(f => !f)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium border transition shadow-sm ${
                hasFilters ? 'bg-blue-50 border-blue-300 text-blue-700' : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
              }`}
            >
              <Filter size={16} />
              Filters
              {hasFilters && <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />}
            </button>
            <button onClick={() => { fetchStudents(); fetchStats(); }}
              className="p-2.5 rounded-xl bg-white border border-gray-200 text-gray-500 hover:text-blue-600 hover:border-blue-300 transition shadow-sm">
              <RefreshCw size={17} />
            </button>
          </div>

          <AnimatePresence>
            {showFilters && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm overflow-hidden">
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <div>
                    <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 block">Department</label>
                    <select value={filterDept} onChange={e => setFilterDept(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm outline-none focus:ring-2 focus:ring-blue-500">
                      <option value="">All Departments</option>
                      {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 block">Year</label>
                    <select value={filterYear} onChange={e => setFilterYear(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm outline-none focus:ring-2 focus:ring-blue-500">
                      <option value="">All Years</option>
                      {[1,2,3,4].map(y => <option key={y} value={y}>{y}{'st nd rd th'.split(' ')[y-1]} Year</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 block">Min GPA</label>
                    <input type="number" min="0" max="10" step="0.5" placeholder="e.g. 7.5"
                      value={filterGpaGte} onChange={e => setFilterGpaGte(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm outline-none focus:ring-2 focus:ring-blue-500" />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 block">Join Year</label>
                    <input type="number" min="2018" max="2030" placeholder="e.g. 2024"
                      value={filterJoinYear} onChange={e => setFilterJoinYear(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm outline-none focus:ring-2 focus:ring-blue-500" />
                  </div>
                </div>
                {hasFilters && (
                  <button onClick={clearFilters}
                    className="mt-3 text-xs text-red-500 hover:text-red-600 font-medium flex items-center gap-1">
                    <X size={13} /> Clear all filters
                  </button>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ══ STUDENT TABLE ══ */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <p className="font-semibold text-gray-700 text-sm">
              {loading ? 'Loading…' : `${students.length} Student${students.length !== 1 ? 's' : ''}`}
              {hasFilters && <span className="ml-2 text-blue-600">(filtered)</span>}
            </p>
            {hasFilters && (
              <button onClick={clearFilters} className="text-xs text-gray-400 hover:text-red-500 flex items-center gap-1">
                <X size={12} /> Clear
              </button>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="px-6 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Student</th>
                  <th className="px-6 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Roll No</th>
                  <th className="px-6 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Department</th>
                  <th className="px-6 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Year</th>
                  <th className="px-6 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">GPA</th>
                  <th className="px-6 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Joined</th>
                  <th className="px-6 py-3.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {loading ? (
                  [1,2,3,4,5].map(i => (
                    <tr key={i} className="animate-pulse">
                      <td colSpan={7} className="px-6 py-4">
                        <div className="h-4 bg-gray-100 rounded w-3/4" />
                      </td>
                    </tr>
                  ))
                ) : students.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-gray-400 text-sm">
                      <Users size={36} className="mx-auto mb-3 opacity-30" />
                      No students found.
                      {hasFilters && (
                        <button onClick={clearFilters} className="block mx-auto mt-2 text-blue-500 hover:underline text-xs">
                          Clear filters
                        </button>
                      )}
                    </td>
                  </tr>
                ) : students.map((s, idx) => (
                  <motion.tr
                    key={s.roll_no}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(idx * 0.03, 0.3) }}
                    className="hover:bg-gray-50/80 transition-colors group"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                          {s.name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-semibold text-gray-900 text-sm">{s.name}</p>
                          <p className="text-xs text-gray-400">{s.email || 'No email'}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-gray-600 font-semibold">{s.roll_no}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase ${DEPT_COLORS[s.department] || 'bg-gray-100 text-gray-600'}`}>
                        {s.department || '—'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {s.year ? `${s.year}${'st nd rd th'.split(' ')[s.year-1]} yr` : '—'}
                    </td>
                    <td className="px-6 py-4">
                      <GpaBadge gpa={s.gpa} />
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">{s.join_year || '—'}</td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button onClick={() => handleEdit(s)}
                          className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition">
                          <Edit2 size={15} />
                        </button>
                        <button onClick={() => handleDelete(s.roll_no, s.name)}
                          className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition">
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ══ AI CHAT PANEL ══ */}
      <AnimatePresence>
        {chatOpen && (
          <motion.div
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 h-full w-[400px] bg-white border-l border-gray-200 flex flex-col shadow-2xl z-40"
          >
            {/* Chat Header */}
            <div className="px-5 py-4 bg-gradient-to-r from-blue-600 to-violet-600 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-white/20 flex items-center justify-center">
                  <Sparkles size={18} className="text-white" />
                </div>
                <div>
                  <p className="font-bold text-white text-sm">Student Agent AI</p>
                  <p className="text-blue-100 text-xs">Natural language student queries</p>
                </div>
              </div>
              <button onClick={() => setChatOpen(false)}
                className="p-1.5 rounded-lg hover:bg-white/20 text-white transition">
                <X size={18} />
              </button>
            </div>

            {/* Quick Chips */}
            <div className="px-4 py-3 border-b border-gray-100 bg-gray-50 flex-shrink-0">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Quick Queries</p>
              <div className="flex flex-wrap gap-1.5">
                {QUICK_CHIPS.map(chip => (
                  <button
                    key={chip}
                    onClick={() => sendChat(chip)}
                    className="text-xs px-2.5 py-1 rounded-full bg-white border border-gray-200 text-gray-600 hover:border-blue-300 hover:text-blue-600 hover:bg-blue-50 transition whitespace-nowrap font-medium"
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map((msg, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                  <ChatMessage msg={msg} />
                </motion.div>
              ))}
              {chatLoading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                    <div className="flex items-center gap-2 text-gray-400 text-xs">
                      <Loader2 size={14} className="animate-spin" />
                      Agent thinking…
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input */}
            <div className="px-4 py-4 border-t border-gray-100 bg-white flex-shrink-0">
              <div className="flex gap-2 bg-gray-50 rounded-xl border border-gray-200 focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-100 transition overflow-hidden">
                <input
                  type="text"
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendChat()}
                  placeholder="Ask the Student Agent…"
                  className="flex-1 bg-transparent px-4 py-3 outline-none text-sm text-gray-700 placeholder-gray-400"
                  disabled={chatLoading}
                />
                <button
                  onClick={() => sendChat()}
                  disabled={!chatInput.trim() || chatLoading}
                  className="m-1.5 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
                >
                  <Send size={15} />
                </button>
              </div>
              <p className="text-center text-xs text-gray-400 mt-2">Powered by UniAgent AI</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ══ TOAST ══ */}
      <AnimatePresence>
        {toastMsg && (
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 40 }}
            className={`fixed bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-2.5 px-5 py-3 rounded-xl shadow-lg text-sm font-medium z-50 ${
              toastMsg.type === 'error'
                ? 'bg-red-600 text-white'
                : 'bg-gray-900 text-white'
            }`}
          >
            {toastMsg.type === 'error'
              ? <AlertCircle size={16} />
              : <CheckCircle size={16} className="text-green-400" />}
            {toastMsg.text}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ══ EDIT MODAL ══ */}
      <AnimatePresence>
        {isEditOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setIsEditOpen(false)} />
            <motion.div initial={{ opacity: 0, scale: 0.93 }} animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.93 }}
              className="bg-white max-w-lg w-full p-7 rounded-2xl border border-gray-100 relative z-10 shadow-2xl max-h-[90vh] overflow-y-auto">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Edit Student</h3>
                  <p className="text-xs text-gray-400 mt-0.5">Update {editingStudent?.name}'s details</p>
                </div>
                <button onClick={() => setIsEditOpen(false)} className="p-1.5 hover:bg-gray-100 rounded-full transition">
                  <X size={18} />
                </button>
              </div>
              <StudentForm
                formData={formData} setFormData={setFormData}
                onSubmit={handleUpdate} onCancel={() => setIsEditOpen(false)}
                title="Edit Student" submitLabel="Save Changes"
              />
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ══ ADD MODAL ══ */}
      <AnimatePresence>
        {isAddOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setIsAddOpen(false)} />
            <motion.div initial={{ opacity: 0, scale: 0.93 }} animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.93 }}
              className="bg-white max-w-lg w-full p-7 rounded-2xl border border-gray-100 relative z-10 shadow-2xl max-h-[90vh] overflow-y-auto">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                    <GraduationCap className="text-blue-600" size={22} />
                    Enroll New Student
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5">Add a new student to the system</p>
                </div>
                <button onClick={() => setIsAddOpen(false)} className="p-1.5 hover:bg-gray-100 rounded-full transition">
                  <X size={18} />
                </button>
              </div>
              <StudentForm
                formData={formData} setFormData={setFormData}
                onSubmit={handleEnroll} onCancel={() => setIsAddOpen(false)}
                title="Enroll Student" submitLabel="Enroll Student"
              />
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Students;
