import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { ArrowLeft, Printer, Download } from 'lucide-react';
import { motion } from 'framer-motion';

const LetterViewer = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [letter, setLetter] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLetter = async () => {
      try {
        const res = await api.get(`/letters/${id}/`);
        setLetter(res.data);
      } catch (err) {
        console.error("Failed to fetch letter:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchLetter();
  }, [id]);

  if (loading) return <div className="p-8 text-center text-gray-500">Loading document...</div>;
  if (!letter) return <div className="p-8 text-center text-red-500 font-bold">Document not found or access denied.</div>;

  const handlePrint = () => {
    window.print();
  };

  // Content generation mapped to formal Block Style
  const currentDate = new Date(letter.created_at).toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric'
  });

  return (
    <div className="min-h-screen bg-gray-50/50 p-4 sm:p-8 font-sans">
      <div className="max-w-4xl mx-auto">
        
        {/* Actions Bar (Hidden on print) */}
        <div className="flex justify-between items-center mb-6 print:hidden">
          <button 
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition font-medium bg-white px-4 py-2 rounded-xl border border-gray-200 shadow-sm"
          >
            <ArrowLeft size={18} /> Back
          </button>
          
          <div className="flex gap-3">
            <button 
              onClick={handlePrint}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white transition font-medium px-4 py-2 rounded-xl shadow-sm"
            >
              <Printer size={18} /> Print
            </button>
            <button 
              onClick={handlePrint}
              className="flex items-center gap-2 bg-gray-900 hover:bg-gray-800 text-white transition font-medium px-4 py-2 rounded-xl shadow-sm"
            >
              <Download size={18} /> Save PDF
            </button>
          </div>
        </div>

        {/* The Formal Letter Page (A4 Paper Style Simulation) */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-white shadow-[0_8px_30px_rgb(0,0,0,0.06)] rounded-sm p-12 sm:p-20 text-gray-900 mx-auto print:shadow-none print:p-0 print:m-0"
          style={{ maxWidth: '210mm', minHeight: '297mm' }}
        >
          {/* Header / Letterhead */}
          <div className="border-b-2 border-gray-800 pb-4 mb-10 text-center">
            <h1 className="text-3xl font-black text-gray-900 uppercase tracking-widest">
              University AI Platform
            </h1>
            <p className="text-sm font-medium text-gray-600 uppercase tracking-widest mt-1">
              Office of the Administration
            </p>
          </div>

          <div className="space-y-6 text-sm sm:text-base leading-relaxed" style={{ fontFamily: '"Times New Roman", Times, serif' }}>
            
            {/* 1. Date */}
            <div>
              Date: <strong>{currentDate}</strong>
            </div>
            
            {/* 2. Recipient Information */}
            <div>
              <p>To,</p>
              <p>Whom It May Concern,</p>
            </div>

            {/* 3. Subject Line */}
            <div className="font-bold underline decoration-1 underline-offset-4">
              <p>Subject: Issuance of {letter.letter_type.toUpperCase()} LETTER</p>
            </div>

            {/* 4. Salutation */}
            <div>
              <p>Respected Sir/Madam,</p>
            </div>

            {/* 5. Body Paragraphs */}
            <div className="space-y-4 text-justify">
              <p>
                This letter is to formally certify the request made by <strong>{letter.student_name}</strong>, 
                bearing Roll ID <strong>{letter.student_roll_id}</strong>.
              </p>
              
              <p>
                <strong>Purpose of Request:</strong> {letter.purpose}
              </p>
              
              {letter.details && (
                <p>
                  <strong>Additional Details:</strong> {letter.details}
                </p>
              )}

              <p>
                This document has been thoroughly reviewed and officially approved by the Head of Department and the Principal's Office online through the University AI Platform. It is issued at the request of the student and does not require a physical signature as it is electronically verified.
              </p>
            </div>

            {/* 6. Closing */}
            <div className="pt-8 space-y-1">
              <p>Sincerely,</p>
              <div className="py-6"></div> {/* Space for Signature */}
              <p className="font-bold uppercase tracking-wider text-gray-800 pt-2 border-t border-gray-300 inline-block">
                Principal's Office
              </p>
              <p className="text-gray-500 text-sm italic">University Administration</p>
            </div>

            {/* Footer / Meta (Verification info) */}
            <div className="mt-20 pt-4 border-t border-gray-200 text-xs text-center text-gray-400 font-mono">
              Document ID: {letter.id} | Generated on: {new Date().toLocaleString()} | Officially Verified Digital Copy
            </div>
          </div>
        </motion.div>

      </div>
    </div>
  );
};

export default LetterViewer;
