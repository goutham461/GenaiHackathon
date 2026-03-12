import React, { useState, useEffect, useRef, useContext } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { AuthContext } from '../context/AuthContext';
import { FileText, CheckCircle, XCircle, Clock, Send, FilePlus, ShieldCheck, Building2, RefreshCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const STATUS_COLORS = {
  pending:        { bg: 'bg-yellow-100', text: 'text-yellow-700', label: '⏳ Pending HOD' },
  hod_approved:   { bg: 'bg-blue-100',   text: 'text-blue-700',   label: '✅ Awaiting Principal' },
  hod_rejected:   { bg: 'bg-red-100',    text: 'text-red-700',    label: '❌ HOD Rejected' },
  final_approved: { bg: 'bg-green-100',  text: 'text-green-700',  label: '🎉 Fully Approved' },
  final_rejected: { bg: 'bg-red-100',    text: 'text-red-700',    label: '❌ Principal Rejected' },
};

const TABS_TEACHER = [
  { id: 'submit',    label: 'Submit Request',      icon: <FilePlus size={16} /> },
  { id: 'hod',       label: 'HOD Dashboard',        icon: <ShieldCheck size={16} /> },
  { id: 'principal', label: 'Principal Dashboard',  icon: <Building2 size={16} /> },
  { id: 'all',       label: 'All Letters',          icon: <FileText size={16} /> },
];

const TABS_STUDENT = [
  { id: 'submit', label: 'Request Letter', icon: <FilePlus size={16} /> },
  { id: 'all',    label: 'My Letters',    icon: <FileText size={16} /> },
];

// Approval timeline helper
const ApprovalTimeline = ({ status }) => {
  const stages = [
    { key: 'submitted',     label: 'Submitted',         done: true },
    { key: 'hod',          label: 'HOD Review',         done: ['hod_approved','final_approved','final_rejected'].includes(status), rejected: status === 'hod_rejected' },
    { key: 'principal',    label: 'Principal Review',   done: ['final_approved','final_rejected'].includes(status), rejected: status === 'final_rejected' },
    { key: 'approved',     label: 'Final Approved',     done: status === 'final_approved' },
  ];
  const isRejected = status === 'hod_rejected' || status === 'final_rejected';
  return (
    <div className="flex items-center gap-0 mt-4">
      {stages.map((s, i) => (
        <React.Fragment key={s.key}>
          <div className="flex flex-col items-center">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-black border-2 transition-all ${
              s.rejected ? 'bg-red-500 border-red-500 text-white' :
              s.done     ? 'bg-green-500 border-green-500 text-white' :
                           'bg-white border-gray-200 text-gray-300'
            }`}>
              {s.rejected ? '✕' : s.done ? '✓' : (i+1)}
            </div>
            <span className={`text-[9px] font-bold mt-1 ${s.rejected ? 'text-red-500' : s.done ? 'text-green-600' : 'text-gray-400'}`}>{s.label}</span>
          </div>
          {i < stages.length - 1 && (
            <div className={`flex-1 h-0.5 mb-4 mx-1 ${
              stages[i+1].done || stages[i+1].rejected ? 'bg-green-400' : 'bg-gray-100'
            }`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
};

const LetterCard = ({ letter, actions, showTimeline = false }) => {
  const s = STATUS_COLORS[letter.status] || STATUS_COLORS.pending;
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className="glass border-white/40 p-6 rounded-3xl shadow-sm">
      <div className="flex justify-between items-start mb-3">
        <div>
          <p className="font-bold text-gray-900">{letter.student_name} <span className="font-mono text-sm text-gray-500">({letter.student_roll_id})</span></p>
          <p className="text-sm text-gray-600 mt-0.5">{letter.purpose}</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-bold ${s.bg} ${s.text}`}>{s.label}</span>
      </div>
      <div className="text-xs text-gray-400 mb-2 flex items-center gap-1">
        <Clock size={12} />
        {new Date(letter.created_at).toLocaleString('en-IN')}
        <span className="mx-2">•</span>
        Type: <strong className="text-gray-600 ml-1">{letter.letter_type?.toUpperCase()}</strong>
      </div>
      {showTimeline && <ApprovalTimeline status={letter.status} />}
      {letter.hod_notes && <p className="text-xs text-blue-600 mt-2">HOD Note: {letter.hod_notes}</p>}
      {letter.principal_notes && <p className="text-xs text-green-600 mt-1">Principal Note: {letter.principal_notes}</p>}
      {letter.status === 'final_approved' && (
        <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-2xl flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-green-700">🎉 Your letter is fully approved!</p>
            <p className="text-xs text-green-600 mt-0.5">Collect the physical copy or view the digital document.</p>
          </div>
          <Link to={`/letters/${letter.id}`} className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-xs font-bold rounded-xl transition flex items-center gap-1 shadow-sm">
            <FileText size={14} /> View Document
          </Link>
        </div>
      )}
      {actions && <div className="flex gap-2 pt-4 border-t border-gray-100 mt-3">{actions}</div>}
    </motion.div>
  );
};

const Letters = () => {
  const { user } = useContext(AuthContext);
  const isTeacher = user?.role === 'teacher';
  const [tab, setTab] = useState('submit');
  const [formData, setFormData] = useState({ student_roll: '', letter_type: 'bonafide', purpose: '', details: '' });
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);
  const [pendingHOD, setPendingHOD] = useState([]);
  const [pendingPrincipal, setPendingPrincipal] = useState([]);
  const [allLetters, setAllLetters] = useState([]);
  const [notes, setNotes] = useState({});
  const [loadingAction, setLoadingAction] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => {
    loadLetters();
    // Auto-refresh for student tab so they see status changes
    if (tab === 'all') {
      pollRef.current = setInterval(loadLetters, 10000);
    }
    return () => clearInterval(pollRef.current);
  }, [tab]);

  const loadLetters = async () => {
    try {
      if (tab === 'hod') {
        const r = await api.get('/letters/pending-hod/');
        setPendingHOD(r.data);
      } else if (tab === 'principal') {
        const r = await api.get('/letters/pending-principal/');
        setPendingPrincipal(r.data);
      } else if (tab === 'all') {
        const r = await api.get('/letters/');
        setAllLetters(r.data);
      }
    } catch (err) { console.error(err); }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitResult(null);
    try {
      const res = await api.post('/letters/generate/', formData);
      setSubmitResult({ ok: true, msg: `Letter request submitted! ID: #${res.data.id}. It will appear in the HOD Dashboard.` });
      setFormData({ student_roll: '', letter_type: 'bonafide', purpose: '', details: '' });
    } catch (err) {
      setSubmitResult({ ok: false, msg: err.response?.data?.error || 'Submission failed.' });
    } finally {
      setSubmitting(false);
    }
  };

  const performAction = async (letterId, endpoint, noteKey) => {
    setLoadingAction(letterId + endpoint);
    try {
      await api.post(`/letters/${letterId}/${endpoint}/`, { notes: notes[noteKey] || '' });
      loadLetters();
    } catch (err) {
      alert(err.response?.data?.error || 'Action failed.');
    } finally {
      setLoadingAction(null);
    }
  };

  const tabs = isTeacher ? TABS_TEACHER : TABS_STUDENT;

  return (
    <div className="p-8 space-y-8 min-h-screen">
      {/* Header */}
      <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
        <h2 className="text-3xl font-bold text-gray-900">📜 Official Letter Desk</h2>
        <p className="text-gray-500 mt-1">Multi-stage approval: Submit → HOD → Principal → Final PDF</p>
      </motion.div>

      {/* Tabs */}
      <div className="flex gap-2 bg-gray-100/60 p-1.5 rounded-2xl w-fit">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold transition-all ${tab === t.id ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {/* SUBMIT TAB */}
        {tab === 'submit' && (
          <motion.div key="submit" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="glass p-8 rounded-3xl border-white/40 shadow-sm max-w-2xl">
            <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
              <FilePlus className="text-blue-500" /> Create New Request
            </h3>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-black uppercase tracking-widest text-gray-500">Student Roll No *</label>
                  <input type="text" placeholder="e.g. CS1001" required
                    className="w-full glass px-4 py-3 rounded-2xl border-white/40 bg-white/50 text-gray-900 font-mono font-bold uppercase outline-none"
                    value={formData.student_roll} onChange={e => setFormData({ ...formData, student_roll: e.target.value.toUpperCase() })} />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-black uppercase tracking-widest text-gray-500">Letter Type *</label>
                  <select className="w-full glass px-4 py-3 rounded-2xl border-white/40 bg-white/50 text-gray-900 font-semibold outline-none"
                    value={formData.letter_type} onChange={e => setFormData({ ...formData, letter_type: e.target.value })}>
                    <option value="bonafide">Bonafide Certificate</option>
                    <option value="noc">No Objection Certificate</option>
                    <option value="internship">Internship Permission</option>
                    <option value="hackathon">Hackathon Permission</option>
                    <option value="academic">Academic Recommendation</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-black uppercase tracking-widest text-gray-500">Purpose *</label>
                <input type="text" placeholder="e.g. SIH 2026 at NIT Chennai" required
                  className="w-full glass px-4 py-3 rounded-2xl border-white/40 bg-white/50 text-gray-900 font-medium outline-none"
                  value={formData.purpose} onChange={e => setFormData({ ...formData, purpose: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-black uppercase tracking-widest text-gray-500">Additional Details</label>
                <textarea rows={3} placeholder="Event dates, venue, any other relevant information..."
                  className="w-full glass px-4 py-4 rounded-2xl border-white/40 bg-white/50 text-gray-900 font-medium outline-none resize-none"
                  value={formData.details} onChange={e => setFormData({ ...formData, details: e.target.value })} />
              </div>
              <button type="submit" disabled={submitting}
                className="w-full bg-blue-600 text-white py-4 rounded-2xl font-black uppercase tracking-widest shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition flex items-center justify-center gap-2 disabled:opacity-60">
                <Send size={18} /> {submitting ? 'Submitting...' : 'Submit for HOD Approval'}
              </button>
            </form>
            {submitResult && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className={`mt-6 p-5 rounded-2xl flex items-start gap-3 ${submitResult.ok ? 'bg-green-50 border border-green-100' : 'bg-red-50 border border-red-100'}`}>
                {submitResult.ok ? <CheckCircle className="text-green-600 mt-0.5" size={20} /> : <XCircle className="text-red-600 mt-0.5" size={20} />}
                <p className={`text-sm font-medium ${submitResult.ok ? 'text-green-800' : 'text-red-800'}`}>{submitResult.msg}</p>
              </motion.div>
            )}
          </motion.div>
        )}

        {/* HOD DASHBOARD TAB */}
        {tab === 'hod' && (
          <motion.div key="hod" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-blue-600 rounded-2xl flex items-center justify-center text-white">
                <ShieldCheck size={20} />
              </div>
              <div>
                <h3 className="font-bold text-gray-900">HOD Approval Portal</h3>
                <p className="text-sm text-gray-500">{pendingHOD.length} letter(s) awaiting your review</p>
              </div>
            </div>
            {pendingHOD.length === 0 ? (
              <div className="glass p-12 rounded-3xl border-white/40 text-center text-gray-400">
                <CheckCircle size={40} className="mx-auto mb-3 text-green-400" />
                <p className="font-bold">All clear! No pending letters.</p>
              </div>
            ) : (
              pendingHOD.map(letter => (
                <LetterCard key={letter.id} letter={letter} actions={
                  <>
                    <input type="text" placeholder="Optional note..."
                      className="flex-1 border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none"
                      onChange={e => setNotes(n => ({ ...n, [`hod_${letter.id}`]: e.target.value }))} />
                    <button onClick={() => performAction(letter.id, 'hod-approve', `hod_${letter.id}`)}
                      disabled={loadingAction === letter.id + 'hod-approve'}
                      className="px-4 py-2 bg-green-600 text-white rounded-xl text-sm font-bold hover:bg-green-700 transition flex items-center gap-1.5">
                      <CheckCircle size={14} /> Approve
                    </button>
                    <button onClick={() => performAction(letter.id, 'hod-reject', `hod_${letter.id}`)}
                      disabled={loadingAction === letter.id + 'hod-reject'}
                      className="px-4 py-2 bg-red-500 text-white rounded-xl text-sm font-bold hover:bg-red-600 transition flex items-center gap-1.5">
                      <XCircle size={14} /> Reject
                    </button>
                  </>
                } />
              ))
            )}
          </motion.div>
        )}

        {/* PRINCIPAL DASHBOARD TAB */}
        {tab === 'principal' && (
          <motion.div key="principal" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-purple-600 rounded-2xl flex items-center justify-center text-white">
                <Building2 size={20} />
              </div>
              <div>
                <h3 className="font-bold text-gray-900">Principal Approval Portal</h3>
                <p className="text-sm text-gray-500">{pendingPrincipal.length} HOD-approved letter(s) for final sign-off</p>
              </div>
            </div>
            {pendingPrincipal.length === 0 ? (
              <div className="glass p-12 rounded-3xl border-white/40 text-center text-gray-400">
                <CheckCircle size={40} className="mx-auto mb-3 text-green-400" />
                <p className="font-bold">No letters awaiting Principal approval.</p>
              </div>
            ) : (
              pendingPrincipal.map(letter => (
                <LetterCard key={letter.id} letter={letter} actions={
                  <>
                    <input type="text" placeholder="Optional note..."
                      className="flex-1 border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none"
                      onChange={e => setNotes(n => ({ ...n, [`principal_${letter.id}`]: e.target.value }))} />
                    <button onClick={() => performAction(letter.id, 'principal-approve', `principal_${letter.id}`)}
                      className="px-4 py-2 bg-purple-600 text-white rounded-xl text-sm font-bold hover:bg-purple-700 transition flex items-center gap-1.5">
                      <CheckCircle size={14} /> Final Approve
                    </button>
                    <button onClick={() => performAction(letter.id, 'principal-reject', `principal_${letter.id}`)}
                      className="px-4 py-2 bg-red-500 text-white rounded-xl text-sm font-bold hover:bg-red-600 transition flex items-center gap-1.5">
                      <XCircle size={14} /> Reject
                    </button>
                  </>
                } />
              ))
            )}
          </motion.div>
        )}

        {/* ALL LETTERS TAB */}
        {tab === 'all' && (
          <motion.div key="all" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
            <div className="flex items-center gap-3">
              <p className="text-sm text-gray-500">{allLetters.length} letter(s)</p>
              <button onClick={() => loadLetters()} className="flex items-center gap-1 text-xs text-blue-600 font-bold hover:text-blue-700">
                <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} /> Refresh
              </button>
              {!isTeacher && <span className="text-xs text-gray-400 bg-gray-50 px-2 py-1 rounded-full">Auto-refreshes every 10s</span>}
            </div>
            {allLetters.length === 0 ? (
              <div className="glass p-12 rounded-3xl border-white/40 text-center text-gray-400">
                <FileText size={40} className="mx-auto mb-3" />
                <p className="font-bold">No letters yet.</p>
              </div>
            ) : (
              allLetters.map(l => <LetterCard key={l.id} letter={l} showTimeline={true} />)
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Letters;
