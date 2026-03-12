import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Users, Search, Plus, Trash2, Edit2, Filter, ChevronRight, X } from 'lucide-react';
import { motion } from 'framer-motion';

const Students = () => {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [editingStudent, setEditingStudent] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [formData, setFormData] = useState({ name: '', department: 'CS', year: 1, roll_no: '', email: '' });

  useEffect(() => {
    fetchStudents();
  }, []);

  const fetchStudents = async () => {
    try {
      const res = await api.get('/students/');
      setStudents(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleEnroll = async (e) => {
    e.preventDefault();
    try {
      await api.post('/students/', formData);
      setIsAddModalOpen(false);
      setFormData({ name: '', department: 'CS', year: 1, roll_no: '', email: '' });
      fetchStudents();
    } catch (err) {
      alert("Failed to enroll student. Check if Roll No already exists.");
    }
  };

  const handleEdit = (student) => {
    setEditingStudent(student);
    setFormData({
      name: student.name,
      department: student.department || 'CS',
      year: student.year || 1,
      roll_no: student.roll_no,
      email: student.email || ''
    });
    setIsModalOpen(true);
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    try {
      await api.patch(`/students/${editingStudent.roll_no}/`, formData);
      setIsModalOpen(false);
      fetchStudents();
    } catch (err) {
      alert("Failed to update student");
    }
  };

  const handleDelete = async (roll_no) => {
    if (window.confirm("Are you sure you want to delete this student?")) {
      try {
        await api.delete(`/students/${roll_no}/`);
        fetchStudents();
      } catch (err) {
        alert("Failed to delete student");
      }
    }
  };

  const filtered = students.filter(s => 
    s.name.toLowerCase().includes(search.toLowerCase()) || 
    s.roll_no.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-8 space-y-8 min-h-screen bg-gray-50/50">
      <div className="flex justify-between items-center">
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <h2 className="text-3xl font-bold text-gray-900">Student Management</h2>
          <p className="text-gray-500">View, enroll, and manage student records across departments.</p>
        </motion.div>
        
        <button 
          onClick={() => {
            setFormData({ name: '', department: 'CS', year: 1, roll_no: '', email: '' });
            setIsAddModalOpen(true);
          }}
          className="flex items-center space-x-2 bg-blue-600 text-white px-5 py-2.5 rounded-xl hover:bg-blue-700 transition shadow-lg shadow-blue-500/20 font-semibold"
        >
          <Plus size={18} />
          <span>Enroll New Student</span>
        </button>
      </div>

      <div className="flex space-x-4">
        <div className="flex-1 glass flex items-center px-4 py-3 rounded-2xl border-white/40">
          <Search className="text-gray-400 mr-3" size={18} />
          <input 
            type="text" 
            placeholder="Search by name or roll number..."
            className="bg-transparent border-none outline-none w-full text-gray-700"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <button className="glass px-5 py-3 rounded-2xl flex items-center space-x-2 text-gray-600 hover:text-blue-600 transition border-white/40 font-medium">
          <Filter size={18} />
          <span>Filters</span>
        </button>
      </div>

      <div className="glass rounded-3xl overflow-hidden border-white/40 shadow-sm">
        <table className="w-full text-left">
          <thead className="bg-gray-100/50 border-b border-gray-200/50">
            <tr>
              <th className="px-6 py-4 font-semibold text-gray-600">Student</th>
              <th className="px-6 py-4 font-semibold text-gray-600">Roll No</th>
              <th className="px-6 py-4 font-semibold text-gray-600">Department</th>
              <th className="px-6 py-4 font-semibold text-gray-600">Year</th>
              <th className="px-6 py-4 font-semibold text-gray-600">Status</th>
              <th className="px-6 py-4"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100/50">
            {loading ? (
              [1, 2, 3].map(i => (
                <tr key={i} className="animate-pulse">
                  <td colSpan="6" className="px-6 py-4 bg-white/30 h-16"></td>
                </tr>
              ))
            ) : filtered.map((s, idx) => (
              <motion.tr 
                key={s.roll_no}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="hover:bg-white/50 transition-colors cursor-pointer group"
              >
                <td className="px-6 py-4">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold">
                      {s.name.charAt(0)}
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">{s.name}</p>
                      <p className="text-xs text-gray-500">{s.email}</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 font-mono text-sm">{s.roll_no}</td>
                <td className="px-6 py-4">
                  <span className="px-3 py-1 rounded-full bg-purple-100 text-purple-600 text-xs font-bold uppercase">
                    {s.department}
                  </span>
                </td>
                <td className="px-6 py-4 text-gray-600">{s.year} Year</td>
                <td className="px-6 py-4">
                  <span className="flex items-center space-x-1.5 text-green-600 text-sm font-medium">
                    <span className="w-2 h-2 rounded-full bg-green-500"></span>
                    <span>Active</span>
                  </span>
                </td>
                <td className="px-6 py-4 text-right opacity-0 group-hover:opacity-100 transition-opacity">
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleEdit(s); }}
                    className="p-2 text-gray-400 hover:text-blue-500 transition-colors"
                  >
                    <Edit2 size={18} />
                  </button>
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleDelete(s.roll_no); }}
                    className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <Trash2 size={18} />
                  </button>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={() => setIsModalOpen(false)}></div>
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass max-w-md w-full p-8 rounded-3xl border-white relative z-10 shadow-2xl"
          >
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-2xl font-bold text-gray-900">Edit Student</h3>
              <button onClick={() => setIsModalOpen(false)} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleUpdate} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Full Name</label>
                <input 
                  type="text" 
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Department</label>
                <select 
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                  value={formData.department}
                  onChange={(e) => setFormData({...formData, department: e.target.value})}
                >
                  <option value="CS">CS</option>
                  <option value="IT">IT</option>
                  <option value="ECE">ECE</option>
                  <option value="EEE">EEE</option>
                  <option value="MECH">MECH</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Academic Year</label>
                <input 
                  type="number" 
                  min="1" max="4"
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                  value={formData.year}
                  onChange={(e) => setFormData({...formData, year: parseInt(e.target.value)})}
                  required
                />
              </div>

              <div className="pt-4 flex space-x-3">
                <button 
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 py-3 font-semibold text-gray-600 hover:bg-gray-100 rounded-xl transition"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  className="flex-1 py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition shadow-lg shadow-blue-500/20"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

      {/* Add Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={() => setIsAddModalOpen(false)}></div>
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass max-w-md w-full p-8 rounded-3xl border-white relative z-10 shadow-2xl"
          >
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-2xl font-bold text-gray-900">Enroll New Student</h3>
              <button onClick={() => setIsAddModalOpen(false)} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleEnroll} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Full Name</label>
                <input 
                  type="text" 
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1.5">Roll No</label>
                  <input 
                    type="text" 
                    placeholder="e.g. CS1001"
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                    value={formData.roll_no}
                    onChange={(e) => setFormData({...formData, roll_no: e.target.value.toUpperCase()})}
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1.5">Department</label>
                  <select 
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                    value={formData.department}
                    onChange={(e) => setFormData({...formData, department: e.target.value})}
                  >
                    <option value="CS">CS</option>
                    <option value="IT">IT</option>
                    <option value="ECE">ECE</option>
                    <option value="EEE">EEE</option>
                    <option value="MECH">MECH</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Email Address</label>
                <input 
                  type="email" 
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Academic Year</label>
                <input 
                  type="number" 
                  min="1" max="4"
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                  value={formData.year}
                  onChange={(e) => setFormData({...formData, year: parseInt(e.target.value)})}
                  required
                />
              </div>

              <div className="pt-4 flex space-x-3">
                <button 
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="flex-1 py-3 font-semibold text-gray-600 hover:bg-gray-100 rounded-xl transition"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  className="flex-1 py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition shadow-lg shadow-blue-500/20"
                >
                  Enroll Student
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </div>
  );
};

export default Students;
