import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Bot, Sparkles, Wand2, Shield, Layers, ArrowRight, Zap, Target, Trash2, MessageSquare, CheckCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const DOMAIN_COLORS = {
  warning: 'red', student: 'blue', attendance: 'green', exam: 'purple',
  faculty: 'indigo', scholarship: 'yellow', letter: 'orange', analytics: 'teal',
};

const DOMAIN_DESCRIPTIONS = {
  warning:    'Predicts student failure risk from attendance data',
  student:    'Manages student enrollment, updates, and records',
  attendance: 'Tracks and marks daily attendance records',
  exam:       'Schedules exams and tracks student results',
  faculty:    'Manages faculty assignments and workload',
  scholarship:'Matches students to eligible scholarships',
  letter:     'Generates permission letters with approval chain',
  analytics:  'Campus-wide stats, reports, and trend analysis',
};

const TEMPLATES = [
  { label: 'Attendance Warning Agent', desc: 'Monitor at-risk students below 75% and calculate days needed to recover' },
  { label: 'Scholarship Matching Agent', desc: 'Check all students against 4 scholarship schemes (TN Laptop, Ambedkar, BC Welfare)' },
  { label: 'Exam Scheduler Agent', desc: 'Schedule midterm exams and allocate rooms to available faculty' },
  { label: 'Letter Generation Agent', desc: 'Generate bonafide and permission letters with HOD and Principal approval' },
];

const AgentFactory = () => {
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [agents, setAgents] = useState([]);
  const [deleting, setDeleting] = useState(null);

  useEffect(() => { fetchAgents(); }, []);

  const fetchAgents = async () => {
    try {
      const res = await api.get('/agents/');
      setAgents(res.data);
    } catch (err) { console.error(err); }
  };

  const detectDomain = (text) => {
    const t = text.toLowerCase();
    if (t.includes('warning') || t.includes('risk') || t.includes('dropout')) return 'warning';
    if (t.includes('scholarship') || t.includes('grant') || t.includes('scheme')) return 'scholarship';
    if (t.includes('exam') || t.includes('midterm') || t.includes('schedule')) return 'exam';
    if (t.includes('letter') || t.includes('noc') || t.includes('bonafide') || t.includes('permission')) return 'letter';
    if (t.includes('attendance') || t.includes('present') || t.includes('absent')) return 'attendance';
    if (t.includes('faculty') || t.includes('professor') || t.includes('workload')) return 'faculty';
    if (t.includes('analytics') || t.includes('stats') || t.includes('pass') || t.includes('report')) return 'analytics';
    return 'student';
  };

  const handleCreate = async (e, prefill = null) => {
    e?.preventDefault();
    const desc = prefill || description;
    if (!desc || loading) return;
    setLoading(true);
    setResult(null);
    try {
      const domain = detectDomain(desc);
      const name = desc.split(' ').slice(0, 4).join(' ').replace(/\b\w/g, c => c.toUpperCase()) + ' Agent';
      const res = await api.post('/agents/', {
        name,
        description: desc,
        domain,
        system_prompt: `You are a ${domain} specialist agent. ${DOMAIN_DESCRIPTIONS[domain]}. Task: ${desc}. Always validate data before taking action. Log all actions.`,
        tools: ['validate', 'query_db', 'respond', 'notify']
      });
      setResult(res.data);
      setDescription('');
      fetchAgents();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    setDeleting(id);
    try {
      await api.delete(`/agents/${id}/`);
      fetchAgents();
    } catch (err) { console.error(err); }
    finally { setDeleting(null); }
  };

  return (
    <div className="p-8 space-y-8 min-h-screen">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <h2 className="text-3xl font-black text-gray-900 tracking-tight">🔧 Agent Factory</h2>
        <p className="text-gray-500 mt-1">Create specialized AI agents in one sentence. Each agent is domain-isolated with strict boundaries.</p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Create Panel */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="glass p-8 rounded-3xl border-white/40 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-blue-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-blue-500/30">
              <Sparkles size={20} />
            </div>
            <div>
              <h3 className="font-bold text-gray-900">Create New Agent</h3>
              <p className="text-xs text-gray-400">Describe what the agent should do</p>
            </div>
          </div>

          {/* Quick Templates */}
          <div className="mb-5">
            <p className="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-3">Quick Templates</p>
            <div className="flex flex-col gap-2">
              {TEMPLATES.map(t => (
                <button key={t.label} onClick={() => setDescription(t.desc)}
                  className="text-left p-3 bg-gray-50 hover:bg-blue-50 hover:border-blue-200 border border-gray-100 rounded-2xl transition group">
                  <p className="text-xs font-bold text-gray-800 group-hover:text-blue-700">{t.label}</p>
                  <p className="text-[10px] text-gray-400 mt-0.5">{t.desc}</p>
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-2 block">Or describe your agent</label>
              <textarea rows={3} placeholder="e.g. An agent that warns students who are below 65% attendance and calculates days needed..."
                className="w-full glass border-white/40 px-4 py-3 rounded-2xl bg-white/80 text-gray-900 text-sm font-medium outline-none resize-none"
                value={description} onChange={e => setDescription(e.target.value)} />
            </div>
            <button type="submit" disabled={!description || loading}
              className="w-full bg-gray-900 text-white py-4 rounded-2xl font-black uppercase tracking-widest hover:bg-gray-800 transition disabled:opacity-50 flex items-center justify-center gap-2">
              {loading ? <><Layers size={18} className="animate-spin" /> Forging...</> : <><Wand2 size={18} /> Forge Agent</>}
            </button>
          </form>

          <AnimatePresence>
            {result && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="mt-5 p-5 bg-green-50 border border-green-200 rounded-2xl">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle size={18} className="text-green-600" />
                  <p className="font-bold text-green-800">Agent Created!</p>
                </div>
                <p className="text-sm text-green-700"><strong>{result.name}</strong></p>
                <p className="text-xs text-green-600 mt-1">Domain: {result.domain} • Tools: {Array.isArray(result.tools) ? result.tools.join(', ') : result.tools}</p>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Active Agents Panel */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="glass p-8 rounded-3xl border-white/40 shadow-sm">
          <h3 className="font-bold text-gray-900 mb-5 flex items-center gap-2">
            <Zap size={18} className="text-blue-500" />
            Active Agents ({agents.length})
          </h3>
          <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
            {agents.map(agent => {
              const color = DOMAIN_COLORS[agent.domain] || 'blue';
              return (
                <div key={agent.id}
                  className="flex items-center justify-between p-4 bg-white/60 border border-gray-100 rounded-2xl hover:bg-white transition group">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl bg-${color}-100 text-${color}-600 flex items-center justify-center`}>
                      <Bot size={18} />
                    </div>
                    <div>
                      <p className="font-bold text-gray-900 text-sm">{agent.name}</p>
                      <p className="text-[10px] uppercase font-bold text-gray-400">{agent.domain} domain</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition">
                    <a href="/chat" className="w-8 h-8 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center hover:bg-blue-200 transition">
                      <MessageSquare size={14} />
                    </a>
                    <button onClick={() => handleDelete(agent.id)} disabled={deleting === agent.id}
                      className="w-8 h-8 bg-red-100 text-red-500 rounded-lg flex items-center justify-center hover:bg-red-200 transition">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              );
            })}
            {agents.length === 0 && (
              <div className="text-center py-8 text-gray-400">
                <Bot size={40} className="mx-auto mb-3 opacity-30" />
                <p className="font-bold text-sm">No agents yet. Create your first one!</p>
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Domain Isolation Explanation */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
        className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Object.entries(DOMAIN_DESCRIPTIONS).map(([domain, desc]) => (
          <div key={domain} className="glass p-5 rounded-2xl border-white/40">
            <div className={`w-8 h-8 bg-${DOMAIN_COLORS[domain]}-100 text-${DOMAIN_COLORS[domain]}-600 rounded-lg flex items-center justify-center mb-3`}>
              <Shield size={14} />
            </div>
            <p className="font-bold text-gray-900 text-sm capitalize">{domain}</p>
            <p className="text-[10px] text-gray-400 mt-1">{desc}</p>
          </div>
        ))}
      </motion.div>
    </div>
  );
};

export default AgentFactory;
