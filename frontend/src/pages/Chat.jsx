import React, { useState, useEffect, useRef, useContext } from 'react';
import api from '../services/api';
import { AuthContext } from '../context/AuthContext';
import { Send, Bot, User as UserIcon, Zap, Loader, ChevronDown, BookOpen, AlertTriangle, Award, FileText, BarChart2, UserCheck, Users, GraduationCap } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const AGENT_ICONS = {
  warning: <AlertTriangle size={14} />,
  student: <Users size={14} />,
  attendance: <UserCheck size={14} />,
  exam: <BookOpen size={14} />,
  faculty: <GraduationCap size={14} />,
  scholarship: <Award size={14} />,
  letter: <FileText size={14} />,
  analytics: <BarChart2 size={14} />,
};

const AGENT_COLORS = {
  warning: 'red', student: 'blue', attendance: 'green', exam: 'purple',
  faculty: 'indigo', scholarship: 'yellow', letter: 'orange', analytics: 'teal',
};

const SUGGESTED = [
  "Check risk for CS1001",
  "Attendance for CS1002",
  "Scholarship for CS1003",
  "List upcoming exams",
  "Show campus analytics",
  "Letter status overview",
];

// Simple markdown-to-JSX renderer
const renderMarkdown = (text) => {
  if (!text) return null;
  const parts = text.split('\n').map((line, i) => {
    if (line.startsWith('**') && line.endsWith('**')) {
      return <p key={i} className="font-bold text-gray-900">{line.replace(/\*\*/g, '')}</p>;
    }
    if (line.startsWith('- ')) {
      const content = line.slice(2).replace(/\*\*(.*?)\*\*/g, (_, m) => `<strong>${m}</strong>`);
      return <li key={i} className="ml-3" dangerouslySetInnerHTML={{ __html: content }} />;
    }
    if (line.match(/^\d+\./)) {
      return <li key={i} className="ml-3 list-decimal" dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />;
    }
    if (line === '') return <div key={i} className="h-2" />;
    const html = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\*(.*?)\*/g, '<em>$1</em>');
    return <p key={i} dangerouslySetInnerHTML={{ __html: html }} />;
  });
  return <div className="text-sm space-y-0.5 leading-relaxed">{parts}</div>;
};

const Chat = () => {
  const { user } = useContext(AuthContext);
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: `👋 Hi ${user?.full_name || user?.email?.split('@')[0]}! I'm the **Campus AI Neural Hub** powered by Gemini.\n\nI have 8 specialized agents:\n- ⚠️ **Warning** — Attendance risk analysis\n- 🎓 **Student** — Enrollment management\n- 📋 **Attendance** — Mark & track records\n- 📚 **Exam** — Schedules & results\n- 👨‍🏫 **Faculty** — Workload tracking\n- 💰 **Scholarship** — Eligibility matching\n- 📄 **Letter** — Permission requests\n- 📊 **Analytics** — Campus insights\n\nWhat would you like to do?`,
      sender: 'bot',
      agentDomain: 'system'
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [showAgentPicker, setShowAgentPicker] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);
  useEffect(() => { fetchAgents(); }, []);

  const fetchAgents = async () => {
    try {
      const res = await api.get('/agents/');
      setAgents(res.data);
      if (res.data.length > 0) setSelectedAgent(res.data[0]);
    } catch (err) { console.error(err); }
  };

  const handleSend = async (text = null) => {
    const msgText = text || input;
    if (!msgText.trim() || loading) return;
    const userMsg = { id: Date.now(), text: msgText, sender: 'user' };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    try {
      const agentId = selectedAgent?.id || agents[0]?.id || 1;
      const res = await api.post(`/agents/${agentId}/chat/`, { message: msgText });
      const botMsg = {
        id: Date.now() + 1,
        text: res.data.response,
        sender: 'bot',
        agentName: res.data.agent,
        agentDomain: selectedAgent?.domain || 'system'
      };
      setMessages(prev => [...prev, botMsg]);
    } catch (err) {
      setMessages(prev => [...prev, { id: Date.now() + 1, text: '⚠️ Service unreachable. Please check backend connection.', sender: 'bot', agentDomain: 'error' }]);
    } finally {
      setLoading(false);
    }
  };

  const domainColor = AGENT_COLORS[selectedAgent?.domain] || 'blue';

  return (
    <div className="h-full flex" style={{ height: 'calc(100vh - 0px)' }}>
      {/* Agent Sidebar */}
      <div className="w-64 border-r border-gray-100 bg-white/50 backdrop-blur-sm flex flex-col p-4 space-y-3 overflow-y-auto">
        <p className="text-[10px] font-black uppercase tracking-widest text-gray-400 px-2 pt-2">Select Agent</p>
        {agents.map(agent => (
          <button key={agent.id} onClick={() => setSelectedAgent(agent)}
            className={`flex items-center gap-3 p-3 rounded-2xl text-left transition-all ${selectedAgent?.id === agent.id ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30' : 'hover:bg-gray-100 text-gray-700'}`}>
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${selectedAgent?.id === agent.id ? 'bg-white/20' : 'bg-gray-100'}`}>
              {AGENT_ICONS[agent.domain] || <Bot size={14} />}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-bold truncate">{agent.name.replace(' Agent', '')}</p>
              <p className={`text-[10px] uppercase font-bold truncate ${selectedAgent?.id === agent.id ? 'text-blue-200' : 'text-gray-400'}`}>{agent.domain}</p>
            </div>
          </button>
        ))}
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100 bg-white/80 backdrop-blur-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-blue-600 flex items-center justify-center text-white">
              <Zap size={20} />
            </div>
            <div>
              <p className="font-bold text-gray-900">{selectedAgent?.name || 'Campus AI'}</p>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Gemini 2.0 Flash • {selectedAgent?.domain || 'Router'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <AnimatePresence>
            {messages.map(msg => (
              <motion.div key={msg.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`flex ${msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'} items-end gap-3 max-w-[80%]`}>
                  <div className={`w-9 h-9 rounded-2xl flex-shrink-0 flex items-center justify-center ${msg.sender === 'user' ? 'bg-gray-900 text-white' : 'bg-blue-600 text-white'}`}>
                    {msg.sender === 'user' ? <UserIcon size={16} /> : <Bot size={16} />}
                  </div>
                  <div className={`p-5 rounded-3xl ${msg.sender === 'user' ? 'bg-gray-900 text-white rounded-tr-none' : 'glass border-white/40 rounded-tl-none'}`}>
                    {msg.agentName && msg.sender === 'bot' && (
                      <p className="text-[9px] font-black uppercase tracking-widest text-blue-500 mb-2">⚡ {msg.agentName}</p>
                    )}
                    {msg.sender === 'bot' ? renderMarkdown(msg.text) : <p className="text-sm">{msg.text}</p>}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          {loading && (
            <div className="flex justify-start">
              <div className="glass border-white/40 px-5 py-4 rounded-3xl rounded-tl-none flex items-center gap-2 text-blue-600">
                <Loader size={16} className="animate-spin" />
                <span className="text-xs font-bold">Thinking with Gemini...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggestions */}
        <div className="px-6 py-3 flex gap-2 overflow-x-auto">
          {SUGGESTED.map(s => (
            <button key={s} onClick={() => handleSend(s)}
              className="flex-shrink-0 text-xs font-semibold px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full hover:bg-blue-100 transition border border-blue-200">
              {s}
            </button>
          ))}
        </div>

        {/* Input */}
        <div className="p-4 border-t border-gray-100 bg-white/80">
          <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="flex items-center gap-3">
            <div className="flex-1 glass border-white/40 rounded-2xl flex items-center px-4 py-3 gap-3">
              <Bot size={18} className="text-blue-500 flex-shrink-0" />
              <input type="text" value={input} onChange={e => setInput(e.target.value)}
                placeholder={`Ask ${selectedAgent?.name || 'Campus AI'}... e.g. "Risk for CS1001"`}
                className="flex-1 bg-transparent border-none outline-none text-sm text-gray-900 placeholder-gray-400"
              />
            </div>
            <button type="submit" disabled={loading || !input.trim()}
              className="w-12 h-12 bg-blue-600 text-white rounded-2xl flex items-center justify-center hover:bg-blue-700 transition disabled:opacity-50 shadow-lg shadow-blue-500/30">
              <Send size={18} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Chat;
