import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, AuthContext } from './context/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import AgentFactory from './pages/AgentFactory';
import Chat from './pages/Chat';
import Students from './pages/Students';
import Faculty from './pages/Faculty';
import Attendance from './pages/Attendance';
import Exams from './pages/Exams';
import Scholarships from './pages/Scholarships';
import Letters from './pages/Letters';
import LetterViewer from './pages/LetterViewer';
import Layout from './layout/Layout';

const PrivateRoute = ({ children }) => {
  const { user, loading } = React.useContext(AuthContext);
  if (loading) return <div>Loading...</div>;
  return user ? children : <Navigate to="/login" />;
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<PrivateRoute><Layout /></PrivateRoute>}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/students" element={<Students />} />
            <Route path="/faculty" element={<Faculty />} />
            <Route path="/attendance" element={<Attendance />} />
            <Route path="/exams" element={<Exams />} />
            <Route path="/scholarships" element={<Scholarships />} />
            <Route path="/letters" element={<Letters />} />
            <Route path="/letters/:id" element={<LetterViewer />} />
            <Route path="/factory" element={<AgentFactory />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/chat" element={<Chat />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
