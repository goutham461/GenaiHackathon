import React, { useContext } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { 
  LayoutDashboard, 
  Settings, 
  MessageSquare, 
  LogOut, 
  Users, 
  UserCheck, 
  GraduationCap, 
  Calendar, 
  Award, 
  FileText,
  BarChart2
} from 'lucide-react';

const Layout = () => {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isTeacher = user?.role === 'teacher';
  const isStudent = user?.role === 'student';

  const navItems = [
    { name: 'Dashboard', path: '/', icon: <LayoutDashboard size={20} />, roles: ['teacher', 'student'] },
    { name: 'Students', path: '/students', icon: <Users size={20} />, roles: ['teacher'] },
    { name: 'Faculty', path: '/faculty', icon: <GraduationCap size={20} />, roles: ['teacher'] },
    { name: 'Attendance', path: '/attendance', icon: <UserCheck size={20} />, roles: ['teacher', 'student'] },
    { name: 'Exams', path: '/exams', icon: <Calendar size={20} />, roles: ['teacher'] },
    { name: 'Scholarships', path: '/scholarships', icon: <Award size={20} />, roles: ['teacher', 'student'] },
    { name: 'Letters', path: '/letters', icon: <FileText size={20} />, roles: ['teacher', 'student'] },
    { name: 'Analytics', path: '/analytics', icon: <BarChart2 size={20} />, roles: ['teacher'] },
    { name: 'Agent Factory', path: '/factory', icon: <Settings size={20} />, roles: ['teacher'] },
    { name: 'Chat', path: '/chat', icon: <MessageSquare size={20} />, roles: ['teacher', 'student'] },
  ].filter(item => item.roles.includes(user?.role));

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 glass-dark flex flex-col justify-between">
        <div className="p-6">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent mb-8">
            UniAgent AI
          </h1>
          <nav className="space-y-2">
            {navItems.map((item) => (
              <Link
                key={item.name}
                to={item.path}
                className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${
                  location.pathname === item.path
                    ? 'glass text-white font-semibold'
                    : 'text-gray-400 hover:text-white hover:bg-white/10'
                }`}
              >
                {item.icon}
                <span>{item.name}</span>
              </Link>
            ))}
          </nav>
        </div>
        
        <div className="p-6 border-t border-gray-700/50">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold">
              {user?.role?.charAt(0).toUpperCase()}
            </div>
            <div>
               <p className="text-sm font-medium">{user?.full_name || user?.email}</p>
               <p className="text-xs text-gray-400 uppercase">{user?.role}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center space-x-2 text-gray-400 hover:text-red-400 transition-colors w-full px-4 py-2"
          >
            <LogOut size={18} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto bg-gray-50">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
