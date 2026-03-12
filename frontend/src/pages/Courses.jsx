import React, { useState, useEffect, useRef } from 'react';
import { 
  BookOpen, Plus, Search, Filter, MessageSquare, Info, 
  Trash2, Edit3, Send, X, AlertCircle, Bookmark, Layers, GitBranch 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import api from '../services/api';
import ReactMarkdown from 'react-markdown';

export default function Courses() {
  const [courses, setCourses] = useState([]);
  const [stats, setStats] = useState({ total_courses: 0, average_credits: 0, department_distribution: [] });
  const [loading, setLoading] = useState(true);
  
  // Filtering
  const [searchTerm, setSearchTerm] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [semFilter, setSemFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  
  // Chat Sidebar
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isAiLoading, setIsAiLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState(null);
  const [formData, setFormData] = useState({
    name: '', code: '', department: '', semester: '', credits: 3, type: 'Core'
  });

  const fetchCourses = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (deptFilter) params.append('department', deptFilter);
      if (semFilter) params.append('semester', semFilter);
      if (typeFilter) params.append('type', typeFilter);
      
      const res = await api.get(`/courses/?${params.toString()}`);
      
      // Client search if needed
      if (searchTerm) {
        const filtered = res.data.filter(c => 
          c.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
          c.code.toLowerCase().includes(searchTerm.toLowerCase())
        );
        setCourses(filtered);
      } else {
        setCourses(res.data);
      }
    } catch (error) {
      console.error("Error fetching courses", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await api.get('/courses/stats/');
      setStats(res.data);
    } catch (error) {
      console.error("Stats err", error);
    }
  };

  useEffect(() => {
    fetchCourses();
    fetchStats();
  }, [deptFilter, semFilter, typeFilter, searchTerm]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const handleAiSubmit = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    
    const userMsg = { role: 'user', content: chatInput };
    setChatMessages(prev => [...prev, userMsg]);
    setChatInput('');
    setIsAiLoading(true);
    
    try {
      const res = await api.post('/agents/1/chat/', { message: userMsg.content });
      setChatMessages(prev => [...prev, { role: 'agent', content: res.data.response }]);
      if (['create', 'add', 'update', 'change', 'delete', 'remove', 'assign'].some(kw => userMsg.content.toLowerCase().includes(kw))) {
         fetchCourses();
         fetchStats();
      }
    } catch (error) {
      setChatMessages(prev => [...prev, { role: 'agent', content: '❌ System error during request.' }]);
    } finally {
      setIsAiLoading(false);
    }
  };
  
  const handleQuickCommand = (cmd) => {
    setChatInput(cmd);
    setIsChatOpen(true);
  };

  const handleSaveCourse = async (e) => {
    e.preventDefault();
    try {
      // Data prep
      const payload = { ...formData };
      if (payload.semester) payload.year = Math.ceil(parseInt(payload.semester) / 2);
      
      if (editingCourse) {
        await api.put(`/courses/${editingCourse.id}/`, payload);
      } else {
        await api.post('/courses/', payload);
      }
      setIsModalOpen(false);
      fetchCourses();
      fetchStats();
    } catch (error) {
       console.error(error);
       alert("Error saving course");
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete course permanently?")) return;
    try {
       await api.delete(`/courses/${id}/`);
       fetchCourses();
       fetchStats();
    } catch (e) {
       console.error(e);
    }
  };

  return (
    <div className="space-y-6 flex relative">
      <div className={`flex-1 transition-all duration-300 ${isChatOpen ? 'mr-96' : ''}`}>
        {/* HEADER */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <BookOpen className="w-6 h-6 text-emerald-500" />
              Course Catalog
            </h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">Manage curriculum, credits, and semesters</p>
          </div>
          <div className="flex gap-3">
            <button
               onClick={() => setIsChatOpen(!isChatOpen)}
               className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-lg hover:from-emerald-600 hover:to-teal-700 font-medium"
            >
               <MessageSquare className="w-4 h-4" />
               <span>AI Assistant</span>
            </button>
            <button
              onClick={() => {
                setEditingCourse(null);
                setFormData({ name: '', code: '', department: '', semester: '', credits: 3, type: 'Core' });
                setIsModalOpen(true);
              }}
              className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white justify-center rounded-lg hover:bg-indigo-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Manual Entry</span>
            </button>
          </div>
        </div>

        {/* STATS */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-100 dark:border-gray-700 flex items-center gap-4">
             <div className="p-3 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 rounded-xl"><Layers className="w-6 h-6"/></div>
             <div>
                <p className="text-sm text-gray-500 font-medium">Total Courses</p>
                <h3 className="text-2xl font-bold">{stats.total_courses}</h3>
             </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-100 dark:border-gray-700 flex items-center gap-4">
             <div className="p-3 bg-amber-100 dark:bg-amber-900/30 text-amber-600 rounded-xl"><Bookmark className="w-6 h-6"/></div>
             <div>
                <p className="text-sm text-gray-500 font-medium">Avg Credits</p>
                <h3 className="text-2xl font-bold">{stats.average_credits} <span className="text-sm text-gray-400">/ course</span></h3>
             </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-100 dark:border-gray-700 flex items-center gap-4">
             <div className="p-3 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 rounded-xl"><GitBranch className="w-6 h-6"/></div>
             <div className="w-full">
                <p className="text-sm text-gray-500 font-medium mb-1">Top Departments</p>
                <div className="flex flex-wrap gap-2 text-sm">
                   {stats.department_distribution.slice(0,3).map(d => (
                      <span key={d.department} className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-gray-700 dark:text-gray-300">
                         {d.department || 'GEN'}: {d.count}
                      </span>
                   ))}
                </div>
             </div>
          </div>
        </div>

        {/* FILTERS */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-100 dark:border-gray-700 mb-6 flex flex-wrap gap-4 items-center">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                 type="text" placeholder="Search by name or code..."
                 className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500 dark:bg-gray-700 dark:border-gray-600"
                 value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <select
              value={deptFilter} onChange={e => setDeptFilter(e.target.value)}
              className="px-4 py-2 border border-gray-200 dark:border-gray-600 rounded-lg dark:bg-gray-700"
            >
              <option value="">All Departments</option>
              {['CS', 'IT', 'ECE', 'EEE', 'MECH', 'CIVIL'].map(d => <option key={d} value={d}>{d}</option>)}
            </select>
            <select
              value={semFilter} onChange={e => setSemFilter(e.target.value)}
              className="px-4 py-2 border border-gray-200 dark:border-gray-600 rounded-lg dark:bg-gray-700"
            >
              <option value="">All Semesters</option>
              {[1,2,3,4,5,6,7,8].map(s => <option key={s} value={s}>Sem {s}</option>)}
            </select>
            <select
              value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
              className="px-4 py-2 border border-gray-200 dark:border-gray-600 rounded-lg dark:bg-gray-700"
            >
              <option value="">All Types</option>
              <option value="Core">Core</option>
              <option value="Elective">Elective</option>
            </select>
            {(deptFilter || semFilter || typeFilter || searchTerm) && (
               <button onClick={() => { setDeptFilter(''); setSemFilter(''); setTypeFilter(''); setSearchTerm(''); }} className="text-red-500 text-sm hover:underline">Clear</button>
            )}
        </div>

        {/* CATALOG GRID */}
        {loading ? (
           <div className="flex justify-center p-12"><div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" /></div>
        ) : courses.length === 0 ? (
           <div className="text-center py-20 bg-gray-50 border border-dashed rounded-xl dark:bg-gray-800/50 dark:border-gray-700">
               <BookOpen className="w-12 h-12 text-gray-300 mx-auto mb-3" />
               <p className="text-gray-500">No courses match your curriculum trace.</p>
           </div>
        ) : (
           <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {courses.map(course => (
                 <div key={course.id} className="bg-white dark:bg-gray-800 rounded-xl p-5 border shadow-sm dark:border-gray-700 hover:shadow-md transition-all group relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-3 opacity-0 group-hover:opacity-100 flex gap-2 transition-opacity">
                        <button onClick={() => { setEditingCourse(course); setFormData(course); setIsModalOpen(true); }} className="p-1.5 bg-gray-100 hover:bg-white text-gray-600 rounded shadow-sm">
                            <Edit3 className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleDelete(course.id)} className="p-1.5 bg-red-50 hover:bg-red-100 text-red-600 rounded shadow-sm">
                            <Trash2 className="w-4 h-4" />
                        </button>
                    </div>
                    
                    <div className="flex items-start justify-between mb-3">
                       <span className={`text-xs font-bold px-2 py-1 uppercase rounded tracking-wider ${
                           course.type === 'Elective' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'
                       }`}>
                          {course.type}
                       </span>
                       <span className="text-indigo-600 font-bold bg-indigo-50 px-2 py-1 rounded text-sm">
                          {course.code}
                       </span>
                    </div>
                    
                    <h3 className="font-bold text-gray-900 dark:text-gray-100 text-lg leading-tight mb-4 min-h-[50px] pr-10">
                       {course.name}
                    </h3>
                    
                    <div className="flex justify-between items-center text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/50 p-2.5 rounded-lg">
                       <div className="flex flex-col">
                          <span className="text-xs uppercase tracking-wider text-gray-400">Dept</span>
                          <span className="font-semibold">{course.department || 'GEN'}</span>
                       </div>
                       <div className="w-px h-8 bg-gray-200 dark:bg-gray-700"></div>
                       <div className="flex flex-col items-center">
                          <span className="text-xs uppercase tracking-wider text-gray-400">Sem</span>
                          <span className="font-semibold">{course.semester || '-'}</span>
                       </div>
                       <div className="w-px h-8 bg-gray-200 dark:bg-gray-700"></div>
                       <div className="flex flex-col items-end">
                          <span className="text-xs uppercase tracking-wider text-gray-400">Credits</span>
                          <span className="font-semibold text-emerald-600">{course.credits}</span>
                       </div>
                    </div>
                 </div>
              ))}
           </div>
        )}
      </div>

      {/* AI CHAT PANEL */}
      <AnimatePresence>
        {isChatOpen && (
          <motion.div
            initial={{ opacity: 0, x: 300 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 300 }}
            className="fixed right-0 top-0 h-screen w-96 bg-white dark:bg-gray-800 shadow-2xl border-l flex flex-col z-50 pt-16"
          >
            <div className="p-4 bg-gradient-to-r from-emerald-600 to-teal-800 text-white flex justify-between items-center shrink-0">
              <div className="flex items-center space-x-2">
                <BookOpen className="w-5 h-5 text-emerald-200" />
                <div>
                  <h3 className="font-semibold">Course AI Agent</h3>
                  <p className="text-xs text-emerald-100">Natural language curriculum manager</p>
                </div>
              </div>
              <button onClick={() => setIsChatOpen(false)} className="text-white hover:bg-white/20 p-1 rounded"><X className="w-5 h-5" /></button>
            </div>

            {chatMessages.length === 0 && (
               <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 m-4 rounded-lg shrink-0">
                  <p className="text-sm font-medium text-emerald-800 dark:text-emerald-300 mb-2">Try saying things like:</p>
                  <div className="flex flex-col gap-2">
                     <button onClick={() => handleQuickCommand("Create a new elective course called Big Data for semester 6 IT students")} className="text-left text-xs bg-white dark:bg-gray-800 p-2 rounded shadow-sm hover:ring-2 border">Create a new elective course called Big Data for semester 6 IT students</button>
                     <button onClick={() => handleQuickCommand("Change credits of Data Structures to 4")} className="text-left text-xs bg-white dark:bg-gray-800 p-2 rounded shadow-sm hover:ring-2 border">Change credits of Data Structures to 4</button>
                     <button onClick={() => handleQuickCommand("Show elective courses for IT department")} className="text-left text-xs bg-white dark:bg-gray-800 p-2 rounded shadow-sm hover:ring-2 border">Show elective courses for IT department</button>
                  </div>
               </div>
            )}

            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50 dark:bg-gray-900/40">
              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] p-3 rounded-2xl text-sm ${msg.role === 'user' ? 'bg-indigo-600 text-white rounded-tr-none' : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 shadow-sm border border-gray-100 dark:border-gray-700 rounded-tl-none markdown-body'}`}>
                     <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                </div>
              ))}
              {isAiLoading && (
                <div className="flex justify-start">
                  <div className="bg-white p-3 rounded-2xl shadow-sm border flex items-center space-x-2">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce"/>
                    <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}/>
                    <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{animationDelay: '0.4s'}}/>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="p-4 bg-white dark:bg-gray-800 border-t shrink-0">
              <form onSubmit={handleAiSubmit} className="flex space-x-2">
                <input
                  type="text" value={chatInput} onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask Course Agent..."
                  className="flex-1 border rounded-xl px-4 py-2 focus:ring-2 focus:ring-emerald-500 dark:bg-gray-700 dark:text-white dark:border-gray-600 outline-none"
                  disabled={isAiLoading}
                />
                <button type="submit" disabled={isAiLoading || !chatInput.trim()} className="bg-emerald-600 text-white p-2 rounded-xl hover:bg-emerald-700 disabled:opacity-50 transition-colors">
                  <Send className="w-5 h-5" />
                </button>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* MANUAL MODAL */}
      <AnimatePresence>
        {isModalOpen && (
          <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
             <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md p-6">
                 <div className="flex justify-between items-center mb-4">
                     <h2 className="text-xl font-bold">{editingCourse ? 'Edit Course' : 'Create Course'}</h2>
                     <button onClick={() => setIsModalOpen(false)}><X className="w-5 h-5 text-gray-500"/></button>
                 </div>
                 <form onSubmit={handleSaveCourse} className="space-y-4">
                     <div>
                         <label className="block text-sm font-medium mb-1">Course Name</label>
                         <input required value={formData.name} onChange={e=>setFormData({...formData, name: e.target.value})} className="w-full border rounded p-2" />
                     </div>
                     <div className="grid grid-cols-2 gap-4">
                         <div>
                             <label className="block text-sm font-medium mb-1">Course Code</label>
                             <input required value={formData.code} onChange={e=>setFormData({...formData, code: e.target.value})} className="w-full border rounded p-2" placeholder="e.g. CS101"/>
                         </div>
                         <div>
                             <label className="block text-sm font-medium mb-1">Department</label>
                             <select className="w-full border rounded p-2" value={formData.department} onChange={e=>setFormData({...formData, department: e.target.value})}>
                                 <option value="">None</option>
                                 <option value="CS">CS</option><option value="IT">IT</option><option value="ECE">ECE</option>
                             </select>
                         </div>
                     </div>
                     <div className="grid grid-cols-3 gap-4">
                         <div>
                             <label className="block text-sm font-medium mb-1">Semester</label>
                             <input type="number" min="1" max="8" value={formData.semester} onChange={e=>setFormData({...formData, semester: e.target.value})} className="w-full border rounded p-2" />
                         </div>
                         <div>
                             <label className="block text-sm font-medium mb-1">Credits</label>
                             <input type="number" min="1" max="6" value={formData.credits} onChange={e=>setFormData({...formData, credits: e.target.value})} className="w-full border rounded p-2" />
                         </div>
                         <div>
                             <label className="block text-sm font-medium mb-1">Type</label>
                             <select className="w-full border rounded p-2 text-sm" value={formData.type} onChange={e=>setFormData({...formData, type: e.target.value})}>
                                 <option value="Core">Core</option>
                                 <option value="Elective">Elective</option>
                             </select>
                         </div>
                     </div>
                     <div className="pt-4 flex justify-end gap-2">
                         <button type="button" onClick={()=>setIsModalOpen(false)} className="px-4 py-2 text-gray-600 bg-gray-100 rounded hover:bg-gray-200">Cancel</button>
                         <button type="submit" className="px-4 py-2 text-white bg-indigo-600 rounded hover:bg-indigo-700">Save Course</button>
                     </div>
                 </form>
             </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
