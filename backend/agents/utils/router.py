"""
Gemini-powered Agent Router (google.genai SDK)
8 domain-isolated agents with real DB actions.
"""
import re
import os
import json
import time
import logging
import random
from datetime import date, timedelta
from django.conf import settings
from django.db.models import Avg, Count


# -- DB Models ------------------------------------------------------------------
from students.models import Student
from attendance.models import AttendanceRecord
from faculty.models import Faculty, FacultyAssignment
from exams.models import Exam, ExamResult
from courses.models import Course
from scholarships.models import ScholarshipScheme
from agents.models import Agent, AgentAction
from letters.models import Letter
from .local_brain import LocalBrain

try:
    from google import genai
    _genai_available = True
except ImportError:
    _genai_available = False


class NLPEngine:
    """Centralized Regex & Entity Extraction Engine for Campus NLP."""
    
    DEPT_PATTERN = r'\b(CS|CSE|IT|ECE|EEE|MECH|CIVIL|AI|DS|DATA\s*SCIENCE|ELECTRONICS|MECHANICAL)\b'
    YEAR_PATTERN = r'\b(1|2|3|4)(?:st|nd|rd|th)?\s*year\b|\b(first|second|third|fourth|final)\s*year\b'
    GPA_GT_PATTERN = r'gpa\s+(?:above|greater|higher|>|>=)\s*(\d+(?:\.\d+)?)'
    GPA_LT_PATTERN = r'gpa\s+(?:below|less|lower|<|<=)\s*(\d+(?:\.\d+)?)'
    GPA_BW_PATTERN = r'gpa\s+between\s+(\d+(?:\.\d+)?)\s+(?:and|&)\s+(\d+(?:\.\d+)?)'
    
    ROLL_PATTERNS = [
        r'roll\s*(?:no|number)?[:\s\-]+([A-Z0-9]+)', # Roll: CS1001
        r'\b([A-Z]{2,4}\d{3,4})\b',                   # CS1001
        r'\b(\d{5,7})\b',                            # 123456
    ]

    @classmethod
    def extract_roll_no(cls, text):
        text = text.upper()
        for pat in cls.ROLL_PATTERNS:
            m = re.search(pat, text)
            if m: return m.group(1)
        return None

    @classmethod
    def extract_dept(cls, text):
        m = re.search(cls.DEPT_PATTERN, text.upper())
        if m:
            d = m.group(1).replace(' ', '')
            if d in ['CSE', 'CS']: return 'CS'
            if d in ['DATA SCIENCE', 'DS']: return 'DS'
            if d == 'MECHANICAL': return 'MECH'
            if d == 'ELECTRONICS': return 'ECE'
            return d
        return None

    @classmethod
    def extract_year(cls, text):
        m = re.search(cls.YEAR_PATTERN, text.lower())
        if m:
            yr_map = {'first':1,'second':2,'third':3,'fourth':4,'final':4}
            val = m.group(2) if m.group(2) else m.group(1)
            return yr_map.get(val, int(val) if val.isdigit() else None)
        return None

    @classmethod
    def extract_gpa_filters(cls, text):
        text = text.lower()
        gt = re.search(cls.GPA_GT_PATTERN, text)
        lt = re.search(cls.GPA_LT_PATTERN, text)
        bw = re.search(cls.GPA_BW_PATTERN, text)
        return {
            'gt': float(gt.group(1)) if gt else None,
            'lt': float(lt.group(1)) if lt else None,
            'bw': (float(bw.group(1)), float(bw.group(2))) if bw else None
        }


class AgentRouter:
    """
    Intelligent Campus AI Router.
    - Gemini 2.0 Flash for NLU + general Q&A
    - 8 domain-isolated agents, each with real DB tools
    - Role-based access: teacher vs student
    """

    AGENT_KEYWORDS = {
        'attendance': [
            'attendance', 'present', 'absent', 'percent', 'days', 'status', 'check',
            'risk', 'safe', 'dropout', 'fail', 'low attendance', 'alert', 'warning',
            'below 75', 'below 65', 'critical attendance', 'debarred', 'debarment', 'danger',
            'poor attendance', 'attendance shortage', 'classes must', 'how many classes',
            'classes needed', 'to reach 75', 'attendance statistics', 'attendance average',
            'predict risk', 'may fall below', 'notify', 'emails', 'inform', 'send notice'
        ],
        'exam': [
            'exam', 'exams', 'schedule', 'timetable', 'midterm', 'final',
            'reschedule', 'postpone', 'cancel', 'move', 'change', 'update',
            'conflict', 'conflicts', 'clash', 'overlap', 'overlapping',
            'plan', 'arrange', 'set up', 'organize', 'tomorrow', 'next week',
            'first', 'upcoming', 'happening', 'scheduled'
        ],
        'faculty':    ['faculty', 'teacher', 'professor', 'prof.', 'workload', 'staff', 'department head', 'hod'],
        'letter':     ['letter', 'permission', 'bonafide', 'noc', 'internship', 'hackathon', 'certificate', 'request'],
        'course':     [
            'course', 'courses', 'subject', 'subjects', 'curriculum', 'credits', 'syllabus',
            'elective', 'core', 'create course', 'add course', 'delete course', 'remove course',
            'assign course', 'update course', 'new course', 'specialization', 'what courses',
            'introduce a subject', 'add a new', 'catalog', 'what subjects', 'change credits',
            'update curriculum', 'adjust the credit', 'modify course info', 'remove the course',
            'cancel the', 'link', 'organize the curriculum', 'review the course', 'manage the course',
            'program'
        ],
        'analytics':  [
            'stats', 'analytics', 'trend', 'report', 'overall', 'campus', 'dashboard',
            'trends', 'graph', 'chart', 'visualize', 'pass percentage', 'enrollment trends'
        ],
        'student':    [
            'enroll', 'delete', 'remove', 'register',
            'list students', 'show students', 'all students', 'new student',
            'admit', 'admission', 'find student', 'search student', 'search for student',
            'update student', 'update gpa', 'change department', 'change dept',
            'modify student', 'edit student', 'update phone', 'update email',
            'how many students', 'count students', 'student count',
            'average gpa', 'top students', 'highest gpa', 'bottom gpa',
            'department distribution', 'student distribution',
            'show all', 'list all', 'display students', 'get students',
            'joined in', 'batch', 'join year', 'gpa above', 'gpa below', 'gpa greater',
            'gpa between', 'first year students', 'second year students',
            'third year students', 'final year students', 'show profile',
            'student profile', 'student record', 'student details', 'student info',
        ],
    }

    # Tracking for quota exhaustion to prevent aggressive retries
    _last_429_time = 0
    _current_key_index = 0
    QUOTA_COOLDOWN = 600  # 10 minutes of silence after 429 if all keys fail

    def __init__(self, user=None):
        self.user = user
        self.role = getattr(user, 'role', 'student')
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize client with current key from pool."""
        keys = getattr(settings, 'GEMINI_API_POOL', [])
        if not keys and getattr(settings, 'GEMINI_API_KEY', None):
            keys = [settings.GEMINI_API_KEY]
            
        if _genai_available and keys:
            try:
                # Rotate key
                idx = AgentRouter._current_key_index % len(keys)
                key = keys[idx]
                self.client = genai.Client(api_key=key)
            except Exception:
                pass

    # -----------------------------------------------------------------
    # MAIN ROUTER
    # -----------------------------------------------------------------
    def route(self, message: str) -> str:
        msg_lower = message.lower()

        # Role-gate first
        if self.role == 'student':
            if any(kw in msg_lower for kw in ['enroll', 'delete', 'analytics', 'pass rate', 'all students']):
                return "Access Denied: This action is restricted to Teachers only."

        # Detect agent domain
        domain = self._detect_domain(msg_lower)

        # Dispatch to domain agent
        dispatch = {
            'student':     self.agent_student,
            'attendance':  self.agent_attendance,
            'exam':        self.agent_exam,
            'faculty':     self.agent_faculty,
            'scholarship': self.agent_scholarship,
            'letter':      self.agent_letter,
            'analytics':   self.agent_analytics,
            'course':      self.agent_course,
        }

        if domain and domain in dispatch:
            # Special case: try domain-specific agent first
            return dispatch[domain](message)

        # FAST-PASS: Handle common conversational queries locally to save Gemini quota
        local_reply = self._local_conversational_reply(msg_lower)
        if local_reply:
            return local_reply

        # TRIPLE-LAYER FALLBACK HIERARCHY:
        # Layer 1 & 2: Gemini -> OpenAI (handled inside _gemini_general)
        res = self._gemini_general(message)
        
        # If cloud APIs failed (indicated by returning fallback/error/None)
        if not res or "[UniAgent AI]" in res or "I couldn't look that up" in res:
             # Layer 3: Offline CampusAI
             from .local_brain import LocalBrain
             local_res = LocalBrain.process(message, self.user)
             if local_res and local_res.get('text'):
                 return local_res.get('text')
        
        return res or self._fallback_help()

    def _local_conversational_reply(self, msg_lower: str) -> str:
        """Handled locally to save Gemini API calls."""
        # Greetings
        if any(w in msg_lower for w in ['hi', 'hello', 'hey', 'good morning', 'good evening']):
            return "Hello! I am your University Agent AI. How can I assist you with the campus database today?"
        
        # Identity
        if any(term in msg_lower for term in ["who are you", "what are you", "your name"]):
            return "Robot I am UniAgent AI!\nI'm the intelligent multi-agent system managing your university database. I have 8 specialized sub-agents (Students, Attendance, Exams, Scholarships, etc.) to help you automate campus administration."
            
        # Help / Capabilities
        if any(term in msg_lower for term in ["what can you do", "help", "how does this work", "commands"]):
            return self._fallback_help()
            
        # Gratitude
        if any(term in msg_lower for term in ["thanks", "thank you", "good job", "awesome"]):
            return "You're very welcome! Let me know if you need help with anything else on campus. :)"
            
        return ""

    def _detect_domain(self, msg_lower: str):
        # Scoring logic for better precision
        scores = {d: 0 for d in self.AGENT_KEYWORDS.keys()}
        
        for domain, keywords in self.AGENT_KEYWORDS.items():
            for kw in keywords:
                if kw in msg_lower:
                    scores[domain] += (2 if kw in msg_lower.split() else 1)
        
        # Priority overrides
        if 'attendance' in msg_lower and ('risk' in msg_lower or 'below' in msg_lower):
            scores['warning'] += 3
        if 'enroll' in msg_lower or 'register student' in msg_lower:
            scores['student'] += 3
        if 'create' in msg_lower and 'course' in msg_lower:
            scores['course'] += 3
            
        best_domain = max(scores, key=scores.get)
        return best_domain if scores[best_domain] > 0 else None

    def extract_roll_no(self, text: str):
        return NLPEngine.extract_roll_no(text)

    # -----------------------------------------------------------------
    # Text-to-SQL-to-Text -- CampusAI Universal Query Engine
    # Uses a SINGLE Gemini call to generate SQL + response template together
    # to minimize API usage.
    # -----------------------------------------------------------------
    def _gemini_student_agent(self, message: str) -> str:
        """Specialized Gemini call for Student Management ONLY (with domain security)."""
        prompt = (
            "You are the Student Management Agent for a university.\n"
            "Your responsibility is to manage student records.\n\n"
            "ALLOWED ACTIONS:\n"
            "- Enroll new students\n"
            "- Update student details (GPA, Dept, Year, Phone, Email)\n"
            "- Delete student records\n"
            "- Retrieve student data/Search\n"
            "- Analytical queries: Counts, Average GPA, Student distribution\n\n"
            "RESTRICTIONS:\n"
            "- You can filter students by: department, year, GPA, joinYear\n"
            "- You are NOT allowed to: manage faculty, manage courses, manage attendance, manage exams\n"
            "- If a request is outside your domain, politely refuse: 'This task belongs to the [Examination/Attendance/Faculty] Agent.'\n\n"
            "DATABASE TABLES (ONLY USE THESE):\n"
            "- students_student: roll_no (student_id), name, department, year, email, phone, marks_12th, caste, annual_income, created_at\n\n"
            "FORMAT: Return JSON {\"sql\": \"SQL query\", \"response\": \"Template with {{RESULTS}}\"}\n"
            "Query: " + message
        )
        # Use existing Gemini logic but with this restricted prompt
        try:
            res = self._gemini_general(prompt, override_prompt=True)
            return res
        except:
            return None

    def _gemini_general(self, message: str, override_prompt: bool = False) -> str:
        if not self.client:
            return self._fallback_help()

        # -- Actual Django SQLite table & column mapping ------------------
        if override_prompt:
             # Just the raw specialized prompt
             combined_prompt = message
        else:
             # Standard general prompt: High-Reliability Schema Injection
             schema = (
                 "UNIVERSITY DB SCHEMA:\n"
                 "- students_student: roll_no (PK), name, department, year, email, phone, marks_12th, annual_income, caste\n"
                 "- collections_attendancerecord: id, roll_no (FK), date, status ('present'/'absent')\n"
                 "- courses_course: id, name, code, department, semester, credits, type ('Core'/'Elective')\n"
                 "- exams_exam: id, course_id (FK), date, room, exam_type ('midterm'/'final'), start_time, end_time\n"
                 "- exams_examresult: id, student_id (FK), exam_id (FK), marks, result_status ('Pass'/'Fail')\n"
                 "- faculty_faculty: id, name, department, email, designation\n"
                 "- scholarships_scholarshipscheme: id, name, eligibility_criteria (JSON), link\n"
                 "- letters_letter: id, student_roll (FK), requested_by (FK), letter_type, purpose, content, status ('pending'/'approved')\n"
                 "\n"
                 "QUERY HINTS:\n"
                 "- Attendance %: ROUND(100.0 * SUM(CASE WHEN status='present' THEN 1 ELSE 0 END) / COUNT(*), 1)\n"
                 "- Pass Rate: 100.0 * COUNT(CASE WHEN marks >= 40 THEN 1 END) / COUNT(*)\n"
                 "- Top Students: ORDER BY marks_12th DESC LIMIT 10\n"
             )

             role_restriction = ""
             if self.role == 'student':
                 user_roll = getattr(self.user, 'username', None) or getattr(self.user, 'roll_no', None)
                 role_restriction = (
                     f"Current User (Student): roll_no='{user_roll}'. "
                     f"STRICT SECURITY: You MUST filter all queries to only show data for roll_no '{user_roll}'. "
                     f"Never expose other students' data."
                 )
             else:
                 role_restriction = f"Current User: Faculty/Admin (Full Access)."

             combined_prompt = (
                 "You are 'UniAgent AI', the intelligent brain of a University Management System.\n"
                 "Use the SCHEMA below to answer the User Message.\n"
                 f"{schema}\n"
                 f"{role_restriction}\n\n"
                 "RULES:\n"
                 "1. SQL: Write a valid SQLite SELECT query. If the request is for an action (enroll, mark), return sql: null.\n"
                 "2. RESPONSE: Write a polite, professional markdown response. Use '{{RESULTS}}' where data will be injected.\n"
                 "3. If no matching data is found, set response to a helpful 'Not found' message.\n"
                 "4. Return ONLY JSON: {\"sql\": \"...\", \"response\": \"...\"}\n\n"
                 f"User Message: '{message}'"
             )


        # Quota Check
        current_time = time.time()
        if (current_time - AgentRouter._last_429_time) < AgentRouter.QUOTA_COOLDOWN:
            return None # Return None to trigger offline brain fallback

        last_err = None
        extracted = {}
        keys = getattr(settings, 'GEMINI_API_POOL', [])
        
        # Try up to 3 keys if we have them
        max_keys = min(len(keys), 3) if keys else 1
        
        for pool_attempt in range(max_keys):
            for attempt in range(2): # 2 retries per key
                try:
                    res = self.client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=combined_prompt
                    )
                    text = res.text.strip().strip('`').strip()
                    if text.lower().startswith('json'):
                        text = text[4:].strip()
                    extracted = json.loads(text)
                    if extracted: break
                except Exception as e:
                    last_err = str(e)
                    print(f"[CampusAI] Key Index {AgentRouter._current_key_index % len(keys) if keys else 0} Error:", last_err[:80])
                    
                    if '429' in last_err or 'quota' in last_err.lower():
                        # Mark this key as likely exhausted (globally for this process)
                        # Rotate to next key for next attempt
                        if keys:
                            AgentRouter._current_key_index += 1
                            self._initialize_client()
                        break # Try next key
                    else:
                        break # Other errors don't usually resolve with retry
            if extracted: break

        if not extracted:
            # Fallback to OpenAI if Gemini pool exhausted
            print(f"[CampusAI] Gemini Pool Exhausted. Trying OpenAI Fallback...")
            openai_res = self._openai_fallback(combined_prompt)
            if openai_res:
                extracted = openai_res
            else:
                return None # Trigger offline brain

        return self._execute_generated_sql(extracted, message)

    def _execute_generated_sql(self, extracted: dict, message: str) -> str:
        """Executes the SQL query and formats the response based on the extracted JSON."""
        sql_query    = extracted.get('sql')
        response_tpl = extracted.get('response') or ''

        # Conversational message -- no DB needed
        if not sql_query:
            return response_tpl or self._fallback_help(message=message)

        # -- Security: Block destructive SQL ------------------------------
        dangerous = ['DROP', 'ATTACH', 'ALTER', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE', 'REPLACE', 'PRAGMA']
        if any(kw in sql_query.upper() for kw in dangerous):
            return "For security reasons, I can only **read** data, not modify it via chat."

        # -- Execute SQL --------------------------------------------------
        from django.db import connection
        import datetime
        class DateEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (datetime.date, datetime.datetime)):
                    return obj.isoformat()
                return super().default(obj)

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                results = [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print("[CampusAI] SQL Error:", str(e))
            return "Error Sorry, I couldn't look that up. Please try rephrasing your question."

        # -- Substitute results into response template --------------------
        if not results:
            # Remove the {{RESULTS}} placeholder and use the template as-is
            return response_tpl.replace("{{RESULTS}}", "").strip() or "No records found matching your request."

        # Format results as a readable list
        def fmt_row(r):
            # Hide raw DB column names; use clean human labels
            parts = []
            for k, v in r.items():
                if v is None:
                    continue
                label = str(k).replace('_', ' ').title()
                parts.append(f"{label}: {v}")
            return " | ".join(parts)

        # Use a list comprehension without slice to avoid generic indexing lints
        formatted_list = [f"- {fmt_row(r)}" for r in results]
        # Only show first 25
        formatted = "\n".join(formatted_list[:25])
        return response_tpl.replace("{{RESULTS}}", f"\n{formatted}")

    def _openai_fallback(self, prompt: str) -> dict:
        """Fallback to OpenAI if Gemini fails."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini", # Use cost-effective gpt-4o-mini
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            text = response.choices[0].message.content
            return json.loads(text)
        except Exception as e:
            print(f"[CampusAI] OpenAI Fallback Error: {e}")
            return {}




    def _fallback_help(self, message: str = "", quota_hit: bool = False) -> str:
        msg = message.lower()
        
        # Conversational fallback logic
        if any(term in msg for term in ["who are you", "what are you", "your name"]):
            return "Robot I am UniAgent AI!\nI'm the intelligent multi-agent system managing your university database. I have 8 specialized sub-agents (Students, Attendance, Exams, Scholarships, etc.) to help you automate campus administration."
            
        if any(term in msg for term in ["what can you do", "help", "how does this work", "commands"]):
            pass # Fall through to the command list below
            
        if any(term in msg for term in ["thanks", "thank you", "good", "great", "awesome"]):
            return "You're very welcome! Let me know if you need help with anything else on campus. :)"
            
        if msg in ["hi", "hello", "hey"]:
            return "Hello! I am your University Agent AI. How can I assist you with the campus database today?"

        note = (
            "\n\n> [Warning] *Gemini AI limit exceeded today. I'm using my built-in offline engine -- all Database commands below still work!*"
            if quota_hit else ""
        )
        return (
            "Hi **Campus AI -- Command Guide:**\n\n"
            "**Attendance:**\n"
            "- `Check risk for CS1001` -- Attendance risk + days needed\n"
            "- `Attendance for CS1002` -- View log\n"
            "- `Low attendance list` -- All students below 75%\n\n"
            "**Students:** (Teacher only)\n"
            "- `Enroll Ravi CS1010` -- Add new student\n"
            "- `List students CS` -- All CS students\n\n"
            "**Exams:**\n"
            "- `Upcoming exams` -- Show schedule\n"
            "- `Top students` -- Rank by marks\n\n"
            "**Scholarships:**\n"
            "- `Scholarship for CS1001` -- Check eligibility\n"
            "- `Eligible for Laptop scheme` -- List eligible students\n\n"
            "**Letters:**\n"
            "- `Generate bonafide for CS1001` -- Create letter\n\n"
            "**Analytics:** (Teacher only)\n"
            "- `Campus analytics` -- Full stats"
            + note
        )

    def _count_risk_students(self):
        count = 0
        for s in Student.objects.all():
            records = AttendanceRecord.objects.filter(roll_no=s)
            total = records.count()
            if total > 0:
                pct = records.filter(status='present').count() / total * 100
                if pct < 75:
                    count += 1
        return count

    # -----------------------------------------------------------------
    # 1. WARNING / ATTENDANCE AGENT – Full NLP Coverage
    # -----------------------------------------------------------------
    # agent_warning was consolidated into agent_attendance

    # -----------------------------------------------------------------
    # 2. STUDENT AGENT – Full NLP Coverage
    # -----------------------------------------------------------------
    def agent_student(self, message: str) -> str:
        """Student Management Agent: Enroll, Update, Delete, List, Search, Analyse."""
        msg_lower = message.lower()

        # --- Role Gate -------------------------------------------------------
        if self.role not in ('teacher', 'admin'):
            if any(kw in msg_lower for kw in [
                'enroll', 'admit', 'delete', 'remove', 'all students', 'list students',
                'update', 'change', 'modify'
            ]):
                return "🔒 **Access Denied:** Only staff can manage student records."
            # Students may only view their own profile
            return self._gemini_student_agent(message) or LocalBrain.process(message, self.user).get('text')

        # --- 1. Domain Security Block ----------------------------------------
        domain_blocks = {
            'exam': 'Examination', 'schedule exam': 'Examination', 'semester': 'Examination',
            'attendance': 'Attendance', 'present': 'Attendance', 'absent': 'Attendance',
            'salary': 'Faculty', 'faculty': 'Faculty',
        }
        for kw, agent_name in domain_blocks.items():
            if kw in msg_lower and 'student' not in msg_lower:
                return (
                    f"⚠️ **Out of Scope:** This task belongs to the **{agent_name} Agent**.\n"
                    f"I am the **Student Management Agent** — I only handle student records."
                )

        # --- Helpers ----------------------------------------------------------
        dept = NLPEngine.extract_dept(message)

        year = NLPEngine.extract_year(message)

        join_year_m = re.search(r'(?:joined?\s+in|batch|admitted?\s+in|from)\s+(20\d{2})', msg_lower)
        join_year = int(join_year_m.group(1)) if join_year_m else None

        gpa_f = NLPEngine.extract_gpa_filters(message)

        roll = self.extract_roll_no(message)

        # --- 2. DELETE -------------------------------------------------------
        if any(kw in msg_lower for kw in ['delete', 'remove']):
            if roll:
                try:
                    s = Student.objects.get(roll_no=roll.upper())
                    sname, semail = s.name, s.email
                    s.delete()
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    User.objects.filter(email=semail).delete()
                    return (
                        f"🗑️ **Deleted Successfully!**\n"
                        f"- **Student:** {sname} ({roll.upper()})\n"
                        f"- Auth account also removed."
                    )
                except Student.DoesNotExist:
                    return f"❌ Student **{roll.upper()}** not found in the database."
            return (
                "⚠️ Please include a **Roll No** to delete a student.\n"
                "Example: *Delete student CS1023*"
            )

        # --- 3. ENROLL / ADMIT -----------------------------------------------
        if any(kw in msg_lower for kw in ['enroll', 'add', 'admit', 'register', 'create', 'new']):
            # Smarter Name Extraction
            name_m = re.search(r'(?:student\s+name|name\s+is|named?|called)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', message)
            if not name_m:
                # Fallback: look for capitalized words after "enroll" or "add"
                name_m = re.search(r'(?:enroll|add|admit|register)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', message)
            
            student_name = name_m.group(1).strip().title() if name_m else None
            
            # Clean up: stop if we hit keywords
            if student_name:
                student_name = re.split(r'\b(in|to|from|dept|department|with|roll|batch|year)\b', student_name, flags=re.IGNORECASE)[0].strip()

            new_roll = self.extract_roll_no(message)
            
            yr_enroll_m = re.search(r'\b(20\d{2})\b', message)
            enroll_join_year = int(yr_enroll_m.group(1)) if yr_enroll_m else None

            enroll_year = year or 1

            if student_name and dept and new_roll:
                try:
                    s = Student.objects.create(
                        roll_no=new_roll.upper(),
                        name=student_name,
                        department=dept,
                        year=enroll_year,
                        join_year=enroll_join_year,
                    )
                    return (
                        f"✅ **Student Enrolled Successfully!**\n"
                        f"- **Name:** {s.name}\n"
                        f"- **Roll No:** {s.roll_no}\n"
                        f"- **Department:** {s.department}\n"
                        f"- **Year:** {s.year}\n"
                        f"- **Join Year:** {s.join_year or 'N/A'}"
                    )
                except Exception as e:
                    return f"❌ Enrollment failed: {str(e)}"
            elif student_name and dept:
                return (
                    f"⚠️ I need a **Roll No** to enroll {student_name} in {dept}.\n"
                    f"Example: *Enroll {student_name} in {dept}, Roll No {dept}1099*"
                )
            # Not enough info — try Gemini
            res = self._gemini_student_agent(message)
            if res and '[UniAgent AI]' not in res: return res
            return "⚠️ Please provide: **student name**, **department**, and **roll number**."

        # --- 4. UPDATE -------------------------------------------------------
        if any(kw in msg_lower for kw in ['update', 'change', 'modify', 'edit']):
            if roll:
                try:
                    s = Student.objects.get(roll_no=roll.upper())
                    updated_fields = []

                    # GPA update
                    gpa_update_m = re.search(r'gpa\s+(?:to\s+)?([0-9]+(?:\.[0-9]+)?)', msg_lower)
                    if gpa_update_m:
                        new_gpa = float(gpa_update_m.group(1))
                        s.gpa = new_gpa
                        updated_fields.append(f'GPA → {new_gpa}')

                    # Department update
                    dept_update_m = re.search(r'department\s+(?:to\s+)?(?:from\s+\S+\s+to\s+)?(\b(?:CS|CSE|IT|ECE|EEE|MECH|CIVIL|AI|DS)\b)', message.upper())
                    if dept_update_m:
                        new_dept = dept_update_m.group(1).replace('CSE', 'CS')
                        s.department = new_dept
                        updated_fields.append(f'Department → {new_dept}')

                    # Year update
                    year_up_m = re.search(r'year\s+(?:to\s+)?(\d)', msg_lower)
                    if year_up_m:
                        s.year = int(year_up_m.group(1))
                        updated_fields.append(f'Year → {s.year}')

                    # Phone update
                    phone_m = re.search(r'phone\s+(?:to\s+|number\s+to\s+)?([0-9]{10})', msg_lower)
                    if phone_m:
                        s.phone = phone_m.group(1)
                        updated_fields.append(f'Phone → {s.phone}')

                    # Email update
                    email_m = re.search(r'email\s+(?:to\s+)?([\w.+-]+@[\w-]+\.[a-z]{2,})', msg_lower)
                    if email_m:
                        s.email = email_m.group(1)
                        updated_fields.append(f'Email → {s.email}')

                    if updated_fields:
                        s.save()
                        return (
                            f"✅ **Updated {s.name} ({roll.upper()}) successfully!**\n"
                            + "\n".join(f"- {f}" for f in updated_fields)
                        )
                    return "⚠️ Could not detect what to update. Specify field (GPA, Department, Year, Phone, Email)."

                except Student.DoesNotExist:
                    return f"❌ Student **{roll.upper()}** not found."
            return "⚠️ Please include a **Roll No** to update. Example: *Update GPA of CS1023 to 8.9*"

        # --- 5. ANALYTICAL QUERIES ------------------------------------------
        if any(kw in msg_lower for kw in ['how many', 'count', 'total', 'average gpa', 'avg gpa', 'distribution', 'top students', 'highest gpa', 'department wise']):

            # Department count
            if ('how many' in msg_lower or 'count' in msg_lower or 'total' in msg_lower) and dept:
                c = Student.objects.filter(department__iexact=dept).count()
                return f"📊 There are **{c} students** in the **{dept}** department."

            # Overall count
            if 'total' in msg_lower or ('how many' in msg_lower and not dept):
                total = Student.objects.count()
                return f"📊 **Total students** enrolled in the university: **{total}**"

            # Average GPA
            if 'average' in msg_lower and 'gpa' in msg_lower:
                qs = Student.objects.all()
                if dept: qs = qs.filter(department__iexact=dept)
                avg = qs.aggregate(Avg('gpa'))['gpa__avg'] or 0
                scope = f"in **{dept}**" if dept else "university-wide"
                return f"📊 Average GPA {scope}: **{avg:.2f}**"

            # Top students by GPA
            if 'top' in msg_lower or 'highest gpa' in msg_lower:
                n_m = re.search(r'top\s+(\d+)', msg_lower)
                n = int(n_m.group(1)) if n_m else 10
                qs = Student.objects.filter(gpa__isnull=False).order_by('-gpa')[:n]
                if not qs.exists(): return "No GPA data available for students."
                lines = [f"{i+1}. **{s.name}** ({s.roll_no}) | {s.department} | GPA: {s.gpa}" for i, s in enumerate(qs)]
                return f"🏆 **Top {n} Students by GPA:**\n" + "\n".join(lines)

            # Department distribution
            if 'distribution' in msg_lower or 'department wise' in msg_lower:
                data = Student.objects.values('department').annotate(count=Count('roll_no')).order_by('-count')
                lines = [f"- **{d['department'] or 'Unknown'}**: {d['count']} students" for d in data]
                total = Student.objects.count()
                return f"📊 **Student Distribution by Department** (Total: {total}):\n" + "\n".join(lines)

        # --- 6. LIST / SHOW / FILTER -----------------------------------------
        if any(kw in msg_lower for kw in ['list', 'show', 'get', 'display', 'view', 'all students', 'students', 'find', 'search']):
            qs = Student.objects.all()

            if dept: qs = qs.filter(department__iexact=dept)
            if year: qs = qs.filter(year=year)
            if join_year: qs = qs.filter(join_year=join_year)

            # GPA filters
            if gpa_f['bw']:
                qs = qs.filter(gpa__gte=gpa_f['bw'][0], gpa__lte=gpa_f['bw'][1])
            elif gpa_f['gt']:
                qs = qs.filter(gpa__gt=gpa_f['gt'])
            elif gpa_f['lt']:
                qs = qs.filter(gpa__lt=gpa_f['lt'])

            # Name search
            name_search_m = re.search(r'(?:find|search|named?|called)\s+(?:student\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', message)
            if name_search_m:
                qs = qs.filter(name__icontains=name_search_m.group(1).strip())

            total = qs.count()
            if total == 0:
                filter_desc = " | ".join(filter(None, [
                    f"Dept: {dept}" if dept else None,
                    f"Year: {year}" if year else None,
                    f"Join: {join_year}" if join_year else None,
                    f"GPA > {gpa_gt_m.group(1)}" if gpa_gt_m else None,
                ]))
                return f"❌ No students found" + (f" ({filter_desc})" if filter_desc else ".")

            students_list = qs.order_by('name')[:20]
            lines = []
            for s in students_list:
                gpa_str = f" | GPA: {s.gpa}" if s.gpa else ""
                join_str = f" | Joined: {s.join_year}" if s.join_year else ""
                lines.append(f"- **{s.name}** ({s.roll_no}) | {s.department or '?'} Yr{s.year or '?'}{gpa_str}{join_str}")

            # Build filter description
            conditions = []
            if dept: conditions.append(f"Dept: {dept}")
            if year: conditions.append(f"Year: {year}")
            if join_year: conditions.append(f"Joined: {join_year}")
            if gpa_f['gt']: conditions.append(f"GPA > {gpa_f['gt']}")
            if gpa_f['lt']: conditions.append(f"GPA < {gpa_f['lt']}")
            if gpa_f['bw']: conditions.append(f"GPA {gpa_f['bw'][0]}-{gpa_f['bw'][1]}")
            cond_str = " | ".join(conditions)

            heading = f"**Found {total} Student(s)**" + (f" [{cond_str}]" if cond_str else "")
            if total > 20:
                heading += f" *(showing first 20)*"
            return heading + ":\n" + "\n".join(lines)

        # --- 7. PROFILE LOOKUP -----------------------------------------------
        if roll:
            try:
                s = Student.objects.get(roll_no=roll.upper())
                gpa_str = f"{s.gpa}" if s.gpa else "N/A"
                return (
                    f"👤 **Student Profile: {s.name}**\n"
                    f"- **Roll No:** {s.roll_no}\n"
                    f"- **Department:** {s.department or 'N/A'}\n"
                    f"- **Year:** {s.year or 'N/A'}\n"
                    f"- **GPA:** {gpa_str}\n"
                    f"- **Join Year:** {s.join_year or 'N/A'}\n"
                    f"- **Email:** {s.email or 'N/A'}\n"
                    f"- **Phone:** {s.phone or 'N/A'}"
                )
            except Student.DoesNotExist:
                return f"❌ Student **{roll.upper()}** not found."

        # --- 8. Fallback to Gemini / Local Brain ------------------------------
        res = self._gemini_student_agent(message)
        if res and '[UniAgent AI]' not in res:
            return res
        fallback = LocalBrain.process(message, self.user)
        if fallback and fallback.get('text'):
            return fallback['text']
        return (
            "🎓 **Student Management Agent**\n"
            "I can help with:\n"
            "- *Show CSE students with GPA above 8*\n"
            "- *Enroll student Ravi in IT, Roll No IT1099*\n"
            "- *Delete student CS1023*\n"
            "- *Update GPA of CS1023 to 8.9*\n"
            "- *How many students are in IT?*\n"
            "- *Show 2024 batch students*\n"
            "- *Top 10 students by GPA*"
        )

    # -----------------------------------------------------------------
    # 2. ATTENDANCE & WARNING AGENT – Full NLP Coverage
    # -----------------------------------------------------------------
    def agent_attendance(self, message: str) -> str:
        """Unified Attendance & Warning Agent."""
        msg_lower = message.lower()
        roll = self.extract_roll_no(message)
        dept = NLPEngine.extract_dept(message)
        year = NLPEngine.extract_year(message)
        
        # Threshold extraction
        thresh_m = re.search(r'(?:below|less|under|<)\s*(\d+(?:\.\d+)?)\s*%?', msg_lower)
        threshold = float(thresh_m.group(1)) if thresh_m else 75.0

        def _get_pct(student):
            recs = AttendanceRecord.objects.filter(roll_no=student)
            tot = recs.count()
            if tot == 0: return None, 0, 0
            pre = recs.filter(status='present').count()
            return round(pre / tot * 100, 1), pre, tot

        def _classes_needed(pre, tot, target=75.0):
            if tot == 0: return 0
            if (pre/tot*100) >= target: return 0
            return int((target/100 * tot - pre) / (1 - target/100)) + 1

        # ─── 1. INDIVIDUAL STUDENT REPORT (Highest Priority) ────────────────
        if roll:
            try:
                s = Student.objects.get(roll_no=roll)
                pct, pre, tot = _get_pct(s)
                
                # A. Mark Attendance
                if any(kw in msg_lower for kw in ['mark', 'present', 'absent']):
                    if self.role != 'teacher': return "🔒 Only faculty can mark attendance."
                    status_val = 'absent' if 'absent' in msg_lower else 'present'
                    AttendanceRecord.objects.update_or_create(roll_no=s, date=date.today(), defaults={'status': status_val})
                    pct, pre, tot = _get_pct(s)
                    return f"✅ **{s.name}** ({roll}) marked **{status_val.upper()}** today. Total: **{pct}%** ({pre}/{tot})"
                
                # B. Prediction / Classes Needed
                if any(kw in msg_lower for kw in ['how many classes', 'needed', 'prediction', 'reach']):
                    needed = _classes_needed(pre, tot, threshold)
                    if needed <= 0: return f"✅ **{s.name}** is safe at **{pct}%**."
                    return f"🔢 **{s.name}** ({pct}%) needs **{needed} more classes** to reach {threshold}%."
                
                # C. General Status
                return (
                    f"📊 **Attendance Certificate for {s.name} ({roll}):**\n"
                    f"- Status: **{'🟢 Safe' if pct >= 75 else '🔴 At Risk'}**\n"
                    f"- Percentage: **{pct}%**\n"
                    f"- Present: **{pre} days** / Total: **{tot} days**"
                )
            except Student.DoesNotExist:
                return f"❌ Student {roll} not found."

        # ─── 2. AGGREGATE QUERIES (Teacher only for sensitive lists) ─────────
        if any(kw in msg_lower for kw in ['risk', 'below', 'low', 'who']):
            qs = Student.objects.all()
            if dept: qs = qs.filter(department=dept)
            if year: qs = qs.filter(year=year)
            
            at_risk = []
            for s in qs:
                pct, pre, tot = _get_pct(s)
                if pct is not None and pct < threshold:
                    at_risk.append(f"- **{s.name}** ({s.roll_no}): **{pct}%**")
            
            if not at_risk: return f"✅ All students are above {threshold}%."
            return f"🚨 **Attendance Warning List (Below {threshold}%):**\n" + "\n".join(at_risk[:15])

        return "📋 **Attendance Agent**: Try 'Check CS1001' or 'Show IT students below 75%'."

        # F. STATISTICS
        if any(kw in msg_lower for kw in ['stats', 'average', 'avg', 'summary']):
            qs = Student.objects.all()
            if dept: qs = qs.filter(department=dept)
            pcts = [p for p in [_get_pct(s)[0] for s in qs] if p is not None]
            if not pcts: return "⚠️ No attendance data found."
            avg = sum(pcts)/len(pcts)
            return f"📊 **Attendance Stats{' for ' + dept if dept else ''}:**\n- Avg: {avg:.1f}%\n- Below 75%: {sum(1 for p in pcts if p < 75)}"

        return "📋 **Attendance Agent**: Try 'Show students below 75%' or 'How many classes does CS1001 need?'"

    # --------------------------------------------------------    # -----------------------------------------------------------------
    # 4. EXAM SCHEDULER AGENT – Full NLP Coverage
    # -----------------------------------------------------------------
    def agent_exam(self, message: str) -> str:
        """Exam Scheduler Agent handling scheduling, conflicts, rescheduling, and timeline viewing."""
        msg_lower = message.lower()
        dept = NLPEngine.extract_dept(message)
        semester = NLPEngine.extract_year(message) # Proxy for year/semester filter

        # Extractor for course name
        course_name = None
        course_m = re.search(r'(?:for|of|exam|on|in)\s+([A-Z][a-zA-Z\s]+?)(?=\s+(?:exam|on|at|in|dept|sem|semester|$))', message)
        if course_m and len(course_m.group(1).strip()) > 3:
            course_name = course_m.group(1).strip()

        # Date extraction
        target_date = None
        if 'tomorrow' in msg_lower: target_date = date.today() + timedelta(days=1)
        elif 'next week' in msg_lower: target_date = date.today() + timedelta(days=7)
        else:
            date_m = re.search(r'\b(\d{1,2}(?:st|nd|rd|th)?\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)\b', message, re.IGNORECASE)
            if date_m:
                 # Simplified date parsing for now
                 pass

        # ─── 1. CONFLICT CHECKING ─────────────────────────────────────────
        if any(kw in msg_lower for kw in ['conflict', 'clash', 'overlap']):
            exams = Exam.objects.all()
            if semester: exams = exams.filter(course__semester__in=[2*semester-1, 2*semester])
            
            conflicts = []
            exams_list = list(exams.select_related('course'))
            for i in range(len(exams_list)):
                for j in range(i + 1, len(exams_list)):
                    e1, e2 = exams_list[i], exams_list[j]
                    if e1.date == e2.date:
                        student_clash = (e1.course.department == e2.course.department and e1.course.semester == e2.course.semester)
                        if student_clash: conflicts.append((e1, e2))

            if not conflicts: return "✅ No exam conflicts detected in the current schedule."
            lines = [f"⚠️ **{e1.course.name}** and **{e2.course.name}** overlap on **{e1.date}**." for e1, e2 in conflicts]
            return "🚨 **Exam Conflicts Detected:**\n" + "\n".join(lines[:10])

        # ─── 2. VIEW TIMETABLE ────────────────────────────────────────────
        if any(kw in msg_lower for kw in ['timetable', 'schedule', 'upcoming', 'when is']):
            qs = Exam.objects.select_related('course').all().order_by('date')
            if dept: qs = qs.filter(course__department=dept)
            if semester: qs = qs.filter(course__semester__in=[2*semester-1, 2*semester])
            
            if not qs.exists(): return f"📅 No exams scheduled{' for ' + dept if dept else ''}."
            
            lines = []
            for e in qs[:15]:
                lines.append(f"- **{e.date.strftime('%b %d')}** | **{e.course.name}** ({e.course.department} Sem {e.course.semester})")
            
            return f"📅 **Upcoming Exam Timetable{' for ' + dept if dept else ''}:**\n" + "\n".join(lines)

        # ─── 3. RESCHEDULE / CANCEL / CREATE (Teachers Only) ──────────────
        if self.role != 'teacher' and any(kw in msg_lower for kw in ['create', 'reschedule', 'cancel', 'move', 'delete']):
            return "🔒 Access Denied: Exam modifications are restricted to faculty."

        if any(kw in msg_lower for kw in ['cancel', 'delete']) and course_name:
            e = Exam.objects.filter(course__name__icontains=course_name).first()
            if e:
                name = e.course.name
                e.delete()
                return f"🗑️ Exam for **{name}** has been cancelled."
            return f"❌ No exam found for {course_name}."

        return "📅 **Exam Agent**: Try 'Show CS timetable' or 'Check for conflicts'."

        # Top 15 display
        lines = []
        for e in qs[:15]:
            time_str = f"| {e.start_time.strftime('%I:%M %p') if e.start_time else 'TBD'}"
            dep_sem = f"{e.course.department or 'N/A'} Sem {e.course.semester or '?'}"
            lines.append(f"- **{e.date.strftime('%b %d')}** {time_str} | **{e.course.name}** ({dep_sem})")
            
        msg = f"📅 **Exam Timetable {'(' + dept + ')' if dept else ''}:**\n" + "\n".join(lines)
        if qs.count() > 15: msg += f"\n\n*(Showing 15 of {qs.count()} exams)*"
        return msg

    # 5. FACULTY AGENT
    def agent_faculty(self, message: str) -> str:
        faculties = Faculty.objects.all()
        
        # If user asks for a specific faculty by name, AI is better at finding them
        if len(message.split()) > 3:
             return self._gemini_general(message) or LocalBrain.process(message, self.user).get('text')
             
        lines = []
        for f in faculties:
            assignments = FacultyAssignment.objects.filter(faculty=f).select_related('course')
            courses = ", ".join([a.course.name for a in assignments]) or "No courses assigned"
            load = assignments.count() * 3  # mock 3 hrs/course
            lines.append(f"- **{f.name}** ({f.department}) | {courses} | Workload: ~{load}hrs/week")
        return "[Teacher] **Faculty Directory:**\n" + "\n".join(lines) if lines else "No faculty records found."

    # -----------------------------------------------------------------
    # 6. SCHOLARSHIP AGENT
    # -----------------------------------------------------------------
    def agent_scholarship(self, message: str) -> str:
        roll = self.extract_roll_no(message)
        msg_lower = message.lower()
        schemes = ScholarshipScheme.objects.all()

        # Regex-based intent extraction -- no Gemini needed
        action = 'unknown'
        target_scheme_name = None
        if not roll:
            if re.search(r'\b(i|me|my|am i)\b', msg_lower):
                action = 'check_self'
            elif 'who' in msg_lower or 'list' in msg_lower or 'eligible' in msg_lower:
                action = 'list_eligible'
            # Extract scheme name from known keywords
            for scheme_kw in ['laptop', 'ambedkar', 'welfare', 'tn laptop']:
                if scheme_kw in msg_lower:
                    target_scheme_name = scheme_kw
                    break


        # Fallback if Gemini failed / Quota exceeded / or check_self is implied
        if action == 'unknown' and not roll:
            # Word boundary matching for " i " to avoid matching "in" or "it"
            if re.search(r'\b(i|me|my|am i)\b', msg_lower):
                action = 'check_self'
            elif 'who' in msg_lower or 'list' in msg_lower or 'eligible' in msg_lower:
                action = 'list_eligible'

        # If it's a self check, auto-assign roll from logged-in user if available
        if action == 'check_self' and not roll and self.user:
            try:
                # We expect the user model email to match the student model email
                s = Student.objects.get(email=self.user.email)
                roll = s.roll_no
            except Student.DoesNotExist:
                return "I couldn't find a matching student profile for your account to check eligibility. Please include your Roll No in the prompt."

        # Did user ask who is eligible for a specific scheme?
        if action == 'list_eligible' and not roll:
            if self.role == 'student':
                return "Access Denied: For privacy reasons, students cannot view the full list of eligible students. You can only check your own eligibility."
            if not schemes:
                return "No active scholarship schemes found."

            target_scheme = None
            if target_scheme_name:
                target_scheme = next((s for s in schemes if target_scheme_name.lower() in s.name.lower()), None)
            if not target_scheme:
                # Try to match scheme name words (e.g. "laptop", "ambedkar")
                msg_lower_words = msg_lower.split()
                target_scheme = next((s for s in schemes if any(w in msg_lower_words for w in s.name.lower().split() if len(w) > 3)), None)
            
            if target_scheme:
                eligible_students = []
                c = target_scheme.eligibility_criteria
                
                for student in Student.objects.all():
                    ok = True
                    if 'income_max' in c and (student.annual_income or 0) > c['income_max']: ok = False
                    if 'marks_min' in c and (student.marks_12th or 0) < c['marks_min']: ok = False
                    if 'caste' in c and student.caste != c['caste']: ok = False
                    
                    if ok:
                        eligible_students.append(f"- **{student.name}** ({student.roll_no}) | {student.department}")
                
                if eligible_students:
                    return f"[Check] **Students currently eligible for {target_scheme.name}:**\n" + "\n".join(eligible_students)
                return f"No students currently eligible for {target_scheme.name}."

        if not roll:
            lines = []
            for s in schemes:
                c = s.eligibility_criteria
                criteria_str = " | ".join([f"{k}: {v}" for k, v in c.items()])
                lines.append(f"- **{s.name}**: {criteria_str}")
            return "[Money Bag] **Active Scholarship Schemes:**\n" + "\n".join(lines)

        try:
            student = Student.objects.get(roll_no=roll)
            eligible, ineligible = [], []
            for s in schemes:
                c = s.eligibility_criteria
                reasons = []
                ok = True
                if 'income_max' in c and (student.annual_income or 0) > c['income_max']:
                    ok = False
                    val = student.annual_income or 0
                    reasons.append(f"income Rs.{val:,.0f} > max Rs.{c['income_max']:,}")
                if 'marks_min' in c and (student.marks_12th or 0) < c['marks_min']:
                    ok = False
                    val = student.marks_12th or 0
                    reasons.append(f"marks {val}% < min {c['marks_min']}%")
                if 'caste' in c and student.caste != c['caste']:
                    ok = False
                    reasons.append(f"caste {student.caste or 'N/A'} is not {c['caste']}")
                if ok:
                    eligible.append(f"NAME: {s.name} -- [Apply]({s.link})")
                else:
                    reasons_str = ", ".join(reasons)
                    ineligible.append(f"NAME: {s.name} ({reasons_str})")

            income_val = student.annual_income or 0
            income_str = f"Rs.{income_val:,.0f}" if student.annual_income is not None else "N/A"
            marks_str = f"{student.marks_12th}%" if student.marks_12th is not None else "N/A"
            caste_str = student.caste if student.caste else "N/A"
            
            out = f"Scholarship Report for {student.name} ({roll})\n"
            out += f"*Caste: {caste_str} | Income: {income_str} | 12th: {marks_str}*\n\n"
            if eligible:
                out += "**Eligible:**\n" + "\n".join(eligible) + "\n\n"
            if ineligible:
                out += "**Ineligible:**\n" + "\n".join(ineligible)
            return out
        except Student.DoesNotExist:
             return self._gemini_general(message) or LocalBrain.process(message, self.user).get('text')

    # -----------------------------------------------------------------
    # 7. LETTER AGENT
    # -----------------------------------------------------------------
    def agent_letter(self, message: str) -> str:
        roll = self.extract_roll_no(message)
        msg = message.lower()

        # Contextual resolution if roll is missing
        if not roll and self.user:
            from .local_brain import CampusAI
            roll = CampusAI.get_roll_from_context(self.user)

        if not roll:
            dashboard = (
                f"[Scroll] **Letter Status Dashboard:**\n"
                f"- User Profile: **{self.user.full_name if self.user else 'Guest'}**\n"
                f"- Status: **Roll No Not Identified**\n\n"
                f"I couldn't automatically link your account to a Student Profile. \n"
                f"**Please include your Roll No in the message**, for example:\n"
                f"- '*Generate on-duty for CS1001*'\n"
                f"- '*Sick leave application CS1001*'"
            )
            return dashboard

        try:
            student = Student.objects.get(roll_no=roll)
            
            # Detect letter type and set formal subject/body
            letter_type = 'bonafide'
            subject = "Application for Bonafide Certificate"
            body = f"With due respect, I {student.name}, a student of {student.department} (Year {student.year}), am requesting a bonafide certificate for my scholarship/bank purposes."
            
            if 'sick' in msg or 'leave' in msg or 'fever' in msg:
                letter_type = 'other'
                subject = "Application for Leave due to Health Issues"
                body = "With due respect, I would like to notify you that I have been suffering from viral fever. As per my physician's advice, I need to take bed rest. I request you to grant me leave."
            elif 'onduty' in msg or 'od' in msg or 'hackathon' in msg:
                letter_type = 'hackathon'
                subject = "Request for On-Duty Permission (Hackathon)"
                body = "I am writing to inform you that I have been selected to participate in a Hackathon event. I request you to grant me On-Duty permission for the duration of the event."
            elif 'noc' in msg:
                letter_type = 'noc'
                subject = "Request for No Objection Certificate (NOC)"
                body = "I am writing to request a No Objection Certificate for my external internship application. I would be highly obliged if you could provide the same."

            # Construct Formal Letter Content
            content = (
                f"{student.name}\n"
                f"{student.department} Department\n"
                f"Roll No: {roll}\n\n"
                f"To,\n"
                f"The Principal,\n"
                f"University Campus Office,\n"
                f"Chennai, Tamil Nadu\n\n"
                f"Date: {date.today().strftime('%d %B %Y')}\n\n"
                f"Subject: {subject}\n\n"
                f"Respected Sir/Madam,\n\n"
                f"{body}\n\n"
                f"I will be highly obliged for your kindness and support in this matter.\n\n"
                f"Thanking You,\n\n"
                f"Yours Obediently,\n"
                f"{student.name}"
            )

            letter = Letter.objects.create(
                student_roll=student,
                requested_by=self.user,
                letter_type=letter_type,
                purpose=subject,
                content=content,
                status='pending'
            )
            
            return (
                f"[Check] **Formal Letter Generated Successfully!** (ID: #{letter.id})\n\n"
                f"**Preview:**\n"
                f"```\n{content}\n```\n\n"
                f"Status: **Pending HOD Approval**\n"
                f"You can track this in your *Letters Dashboard*."
            )
        except Student.DoesNotExist:
            return f"Student {roll} not found."

    # -----------------------------------------------------------------
    # 8. ANALYTICS AGENT
    # -----------------------------------------------------------------
    def agent_analytics(self, message: str) -> str:
        msg_lower = message.lower()
        # --- Custom Data Visualizations ---
        if any(kw in msg_lower for kw in ['enrollment trend', 'trend', 'year-wise', 'year wise']) and 'enrollment' in msg_lower:
             return "📈 **Year-Wise Enrollment Trends**\n\nHere is the historical data showing our campus enrollment growth over the recent years:\n\n[CHART:bar:/api/students/enrollment-trends/]"
             
        if any(kw in msg_lower for kw in ['pass percentage', 'pass rate', 'compare', 'department-wise']) and ('pass' in msg_lower or 'department' in msg_lower):
             return "📊 **Department-wise Pass Percentages**\n\nHere is the comparison of exam pass rates across all departments:\n\n[CHART:bar:/api/exam-results/pass-percentages/]"

        # Analytics is perfect for AI-first processing
        res = self._gemini_general(message)
        if res and "[UniAgent AI]" not in res:
             return res
             
        # Local fallback if keywords match
        local_res = LocalBrain.process(message, self.user)
        if local_res and local_res.get('text'):
             return local_res.get('text')

        if self.role == 'student':
            return "Analytics dashboard is restricted to staff only."

        total_students = Student.objects.count()
        avg_marks = Student.objects.aggregate(avg=Avg('marks_12th'))['avg'] or 0
        total_records = AttendanceRecord.objects.count()
        present = AttendanceRecord.objects.filter(status='present').count()
        overall_att = (present / total_records * 100) if total_records else 0

        dept_stats = {}
        for dept in ['CS', 'IT', 'ECE']:
            count = Student.objects.filter(department=dept).count()
            if count:
                dept_stats[dept] = count

        # Risk counts
        high_risk, medium_risk, safe = 0, 0, 0
        for s in Student.objects.all():
            recs = AttendanceRecord.objects.filter(roll_no=s)
            total = recs.count()
            if total:
                pct = recs.filter(status='present').count() / total * 100
                if pct < 65: high_risk += 1
                elif pct < 75: medium_risk += 1
                else: safe += 1

        results_total = ExamResult.objects.count()
        passing = ExamResult.objects.filter(marks__gte=40).count()
        pass_rate = (passing / results_total * 100) if results_total else 0

        dept_line = " | ".join([f"{k}: {v}" for k, v in dept_stats.items()])
        return (
            f"[Analytics] **Campus Analytics Dashboard**\n\n"
            f"**Enrollment:**\n"
            f"- Total Students: {total_students}\n"
            f"- By Dept: {dept_line}\n"
            f"- Avg 12th Marks: {avg_marks:.1f}%\n\n"
            f"**Attendance:**\n"
            f"- Overall: {overall_att:.1f}%\n"
            f"-  High Risk: {high_risk} |  Medium: {medium_risk} |  Safe: {safe}\n\n"
            f"**Exam Performance:**\n"
            f"- Pass Rate: {pass_rate:.1f}% ({passing}/{results_total})"
        )

    # -----------------------------------------------------------------
    # 9. COURSE MANAGEMENT AGENT
    # -----------------------------------------------------------------
    def agent_course(self, message: str) -> str:
        """Course Management Agent: Rebuilt for higher reliability and NLP precision."""
        msg_lower = message.lower()
        dept = NLPEngine.extract_dept(message)
        semester = NLPEngine.extract_year(message) # Proxy for year/semester filter

        # ─── 0. HELPERS / EXTRACTORS ──────────────────────────────────────
        def _extract_course_name(text):
            # Try specific patterns first
            m = re.search(r'(?:called|named|course|subject)\s+([A-Z][a-zA-Z\s0-9]+?)(?=\s+(?:for|to|in|from|credits|dept|sem|semester|$))', text, re.IGNORECASE)
            if m and len(m.group(1).strip()) > 2:
                name = m.group(1).strip().title()
                if name.lower() not in ['course', 'subject', 'a', 'the', 'new']:
                    return name
            return None

        # ─── 1. VIEW / LIST COURSES ───────────────────────────────────────
        if any(kw in msg_lower for kw in ['show', 'list', 'what subjects', 'curriculum', 'view']):
            qs = Course.objects.all().order_by('semester', 'name')
            if dept: qs = qs.filter(department=dept)
            if semester: qs = qs.filter(semester__in=[2*semester-1, 2*semester])
            
            if not qs.exists(): return "📚 No courses found matching your criteria."
            
            lines = [f"- **{c.name}** ({c.code}) | Sem {c.semester} | {c.credits} Credits" for c in qs[:20]]
            header = f"📚 **Curriculum{' for ' + dept if dept else ''}{' Year ' + str(semester) if semester else ''}**\n"
            return header + "\n".join(lines)

        # ─── 2. CREATE / ADD COURSE (Teachers Only) ───────────────────────
        if any(kw in msg_lower for kw in ['create', 'add ', 'introduce', 'new course']):
            if self.role != 'teacher': return "🔒 Only faculty can modify the curriculum."
            
            course_name = _extract_course_name(message)
            if not course_name: return "⚠️ Please specify the course name. Example: *Create a new course called Machine Learning for semester 6*."
            
            code = (course_name[:2].upper() + str(random.randint(1000, 9999)))
            Course.objects.create(
                name=course_name, 
                code=code, 
                department=dept or "General", 
                semester=semester or 1,
                credits=3
            )
            return f"✅ **{course_name}** ({code}) has been added to the curriculum."

        # ─── 3. DELETE / REMOVE ───────────────────────────────────────────
        if any(kw in msg_lower for kw in ['delete', 'remove']) and self.role == 'teacher':
            course_name = _extract_course_name(message)
            if course_name:
                c = Course.objects.filter(name__icontains=course_name).first()
                if c:
                    name = c.name
                    c.delete()
                    return f"🗑️ **{name}** has been removed from the curriculum."
            return "⚠️ Please specify which course to delete."

        return "📚 **Course Agent**: Try 'Show IT courses' or 'Add new course AI to semester 5'."
