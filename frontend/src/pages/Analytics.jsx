import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import { Activity, TrendingUp, Users, Send } from 'lucide-react';

// Custom Markdown Component to intercept and render [CHART:bar:url] syntax
const MarkdownWithCharts = ({ text }) => {
  // We use regex to split the text into regular markdown and chart tags
  const parts = text.split(/(\[CHART:bar:[^\]]+\])/);

  return (
    <>
      {parts.map((part, index) => {
        if (part.startsWith('[CHART:bar:')) {
          const endpoint = part.replace('[CHART:bar:', '').replace(']', '').trim();
          return <DynamicChart key={index} endpoint={endpoint} />;
        }
        return <ReactMarkdown key={index} remarkPlugins={[remarkGfm]}>{part}</ReactMarkdown>;
      })}
    </>
  );
};

// Component to fetch data and render a Recharts BarChart based on the endpoint
const DynamicChart = ({ endpoint }) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = localStorage.getItem('token');
        const config = token ? { headers: { Authorization: `Token ${token}` } } : {};
        const res = await axios.get(`http://localhost:8000${endpoint}`, config);
        setData(res.data);
      } catch (err) {
        setError('Failed to load chart data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [endpoint]);

  if (loading) return <div className="p-4 bg-gray-50 rounded text-center animate-pulse">Loading Chart...</div>;
  if (error) return <div className="p-4 bg-red-50 text-red-600 rounded text-center">{error}</div>;
  if (!data || data.length === 0) return <div className="p-4 bg-gray-50 rounded text-center">No data available</div>;

  // Determine keys dynamically based on first object
  const keys = Object.keys(data[0]);
  const xAxisKey = keys[0]; // Usually 'year' or 'department'
  const barKeys = keys.slice(1); // The numeric metrics

  return (
    <div className="w-full h-72 mt-4 bg-white p-4 rounded-xl shadow-sm border border-gray-100">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
          <XAxis dataKey={xAxisKey} axisLine={false} tickLine={false} />
          <YAxis axisLine={false} tickLine={false} />
          <Tooltip 
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
          />
          <Legend wrapperStyle={{ paddingTop: '20px' }} />
          {barKeys.map((key, i) => (
            <Bar 
              key={key} 
              dataKey={key} 
              fill={i === 0 ? "#6366f1" : "#10b981"} // Indigo and Emerald
              radius={[4, 4, 0, 0]} 
              barSize={40}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default function Analytics() {
  const [overview, setOverview] = useState(null);
  
  // Chat state
  const [messages, setMessages] = useState([{
    sender: 'agent',
    text: "👋 Hi! I'm the **Analytics Agent**.\n\nI can generate data visualizations and campus insights. Try asking me:\n- *Show year-wise enrollment trends*\n- *Compare pass percentage across departments*"
  }]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const endOfMessagesRef = useRef(null);

  // Fetch basic top-level metrics
  useEffect(() => {
    const fetchOverview = async () => {
      try {
        const token = localStorage.getItem('token');
        const config = token ? { headers: { Authorization: `Token ${token}` } } : {};
        const res = await axios.get('http://localhost:8000/api/students/stats/', config);
        setOverview(res.data);
      } catch (err) {
        console.error(err);
      }
    };
    fetchOverview();
  }, []);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg = input;
    setMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setInput('');
    setIsTyping(true);

    try {
      const token = localStorage.getItem('token');
      // Using generic agent endpoint which will route to agent_analytics natively
      const res = await axios.post('http://localhost:8000/api/agents/chat/', 
        { message: userMsg },
        { headers: { Authorization: `Token ${token}` } }
      );
      setMessages(prev => [...prev, { sender: 'agent', text: res.data.response || res.data }]);
    } catch (error) {
      setMessages(prev => [...prev, { sender: 'agent', text: "❌ Connection error." }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleQuickCommand = (cmd) => {
    setInput(cmd);
  };

  return (
    <div className="flex h-[calc(100vh-80px)] space-x-6 p-6 overflow-hidden bg-gray-50/50">
      
      {/* LEFT COLUMN: Static Dashboard Metrics */}
      <div className="w-1/3 flex flex-col space-y-6">
        <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-3xl p-6 text-white shadow-lg">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-3 bg-white/20 rounded-2xl backdrop-blur-md">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-2xl font-bold">Campus Analytics</h1>
          </div>
          <p className="text-indigo-100 mb-6">Real-time data insights generated by the neural hub.</p>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white/10 rounded-2xl p-4 backdrop-blur-sm">
              <div className="text-indigo-200 text-sm font-medium mb-1 flex items-center">
                <Users className="w-4 h-4 mr-2" /> Total Enrolled
              </div>
              <div className="text-3xl font-bold">{overview?.total || '--'}</div>
            </div>
            <div className="bg-white/10 rounded-2xl p-4 backdrop-blur-sm">
              <div className="text-indigo-200 text-sm font-medium mb-1 flex items-center">
                <TrendingUp className="w-4 h-4 mr-2" /> Avg GPA
              </div>
              <div className="text-3xl font-bold">{overview?.avg_gpa || '--'}</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100 flex-1">
           <h2 className="text-lg font-bold text-gray-800 mb-4">Quick Insights</h2>
           <div className="space-y-3">
             <button onClick={() => handleQuickCommand('Show year-wise enrollment trends')} className="w-full text-left p-4 rounded-xl hover:bg-indigo-50 transition border border-gray-100 group">
               <div className="font-medium text-gray-700 group-hover:text-indigo-600">Enrollment Trends</div>
               <div className="text-xs text-gray-400 mt-1">Generate a bar chart of yearly admissions</div>
             </button>
             <button onClick={() => handleQuickCommand('Compare pass percentage across departments')} className="w-full text-left p-4 rounded-xl hover:bg-purple-50 transition border border-gray-100 group">
               <div className="font-medium text-gray-700 group-hover:text-purple-600">Pass Percentages</div>
               <div className="text-xs text-gray-400 mt-1">Visualize performance by department</div>
             </button>
             <button onClick={() => handleQuickCommand('Show top 5 students by GPA')} className="w-full text-left p-4 rounded-xl hover:bg-pink-50 transition border border-gray-100 group">
               <div className="font-medium text-gray-700 group-hover:text-pink-600">Top Performers</div>
               <div className="text-xs text-gray-400 mt-1">Query the highest GPA students</div>
             </button>
           </div>
        </div>
      </div>

      {/* RIGHT COLUMN: AI Chat Panel */}
      <div className="w-2/3 flex flex-col bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
        
        {/* Header */}
        <div className="p-4 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-3 h-3 bg-indigo-500 rounded-full animate-pulse shadow-[0_0_10px_rgba(99,102,241,0.5)]"></div>
            <div>
              <div className="font-semibold text-gray-800">Analytics Agent</div>
              <div className="text-xs text-gray-500">Gemini 2.0 Flash + Recharts</div>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-[#FAFAFA]">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-2xl p-4 shadow-sm ${
                msg.sender === 'user' 
                  ? 'bg-indigo-600 text-white rounded-tr-sm' 
                  : 'bg-white border border-gray-100 text-gray-700 rounded-tl-sm prose prose-sm prose-indigo'
              }`}>
                {msg.sender === 'user' ? (
                  msg.text 
                ) : (
                  <MarkdownWithCharts text={msg.text} />
                )}
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-sm p-4 flex space-x-2">
                <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          )}
          <div ref={endOfMessagesRef} />
        </div>

        {/* Input */}
        <form onSubmit={sendMessage} className="p-4 bg-white border-t border-gray-100">
          <div className="relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask for data visualizations, trends, or stats..."
              className="w-full pl-5 pr-14 py-4 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-indigo-100 focus:bg-white transition-all text-sm outline-none"
            />
            <button
              type="submit"
              disabled={!input.trim() || isTyping}
              className="absolute right-2 p-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition transform hover:scale-105 active:scale-95 shadow-[0_4px_14px_0_rgba(99,102,241,0.39)]"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}
