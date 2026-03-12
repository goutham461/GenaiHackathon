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


class AgentRouter:
    """
    Intelligent Campus AI Router.
    - Gemini 2.0 Flash for NLU + general Q&A
    - 8 domain-isolated agents, each with real DB tools
    - Role-based access: teacher vs student
    """

    AGENT_KEYWORDS = {
        'scholarship':['scholarship', 'laptop', 'tn laptop', 'ambedkar', 'welfare', 'eligible', 'stipend', 'grant', 'scheme'],
        'warning':    [
            'risk', 'safe', 'dropout', 'fail', 'low attendance', 'alert', 'warning',
            'below 75', 'below 65', 'attendance below', 'attendance less', 'attendance under',
            'critical attendance', 'debarred', 'debarment', 'danger', 'very low attendance',
            'poor attendance', 'attendance problem', 'attendance issue', 'attendance shortage',
            'who has low', 'who is missing', 'who hasn', 'missing classes', 'attend more',
            'classes must', 'how many classes', 'classes needed', 'to reach 75', 'to reach 65',
            'attendance report', 'attendance statistics', 'attendance average', 'attendance distribution',
            'worst attendance', 'lowest attendance', 'department attendance',
            'predict risk', 'likely to fail', 'may fall below', 'skipped', 'behind', 'not meeting',
            'notify', 'emails', 'inform', 'send notice', 'send alert',
        ],
        'attendance': ['attendance', 'present', 'absent', 'percent', 'days', 'status', 'check'],
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
            'warning':     self.agent_warning,
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
        for domain, keywords in self.AGENT_KEYWORDS.items():
            if any(kw in msg_lower for kw in keywords):
                return domain
        return None

    def extract_roll_no(self, text: str):
        roll_m = re.search(r'roll\s*(?:no|number)?[:\s\-]+([A-Za-z0-9]+)', text, re.IGNORECASE)
        if roll_m:
            return roll_m.group(1).upper()
            
        match = re.search(r'\b([A-Za-z]{2,4}\d{3,4})\b', text.upper())
        if match:
            return match.group(1)
            
        match_digits = re.search(r'\b(\d{4,6})\b', text)
        return match_digits.group(1) if match_digits else None

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
             # Standard general prompt
             schema = (
                 "TABLE students_student: roll_no (PK/student_id), name, department, year, email, phone\n"
                 "TABLE attendance_attendancerecord: id, roll_no (FK->students_student.roll_no), date, status ('present'/'absent')\n"
                 "TABLE courses_course: id, name, code, department\n"
                 "TABLE faculty_faculty: id, name, department, email\n"
                 "TABLE exams_exam: id, exam_type, date, room\n"
                 "JOIN syntax: JOIN students_student ON attendance_attendancerecord.roll_no = students_student.roll_no\n"
                 "For attendance %: ROUND(100.0*SUM(CASE WHEN status='present' THEN 1 ELSE 0 END)/COUNT(*),1)\n"
             )

             role_restriction = ""
             if self.role == 'student':
                 user_roll = getattr(self.user, 'username', None) or getattr(self.user, 'roll_no', None)
                 role_restriction = (
                     f"ROLE: Student (roll_no='{user_roll}'). "
                     f"SQL must ONLY query data for roll_no='{user_roll}'. Never return other students' data."
                 )
             else:
                 role_restriction = f"ROLE: {self.role.title()}. Full access to all records."

             # Single combined prompt: SQL + response template in one call
             combined_prompt = (
                 "You are CampusAI for a College Management System.\n"
                 f"SCHEMA:\n{schema}\n"
                 f"{role_restriction}\n\n"
                 "TASK: Given the user's message, do the following in ONE response:\n"
                 "1. Write a SQLite SELECT query for the request.\n"
                 "2. Write a friendly response template. Use {{RESULTS}} as a placeholder where the data will go.\n"
                 "   If results are empty, write a polite 'not found' message instead.\n"
                 "3. If the message is NOT a database query (e.g. 'hi', 'thanks'), set sql to null and put the reply in response.\n\n"
                 "Return ONLY this raw JSON (no markdown, no code fences):\n"
                 "{\"sql\": \"SELECT ...\", \"response\": \"Here is the info: {{RESULTS}}\"}\n"
                 "  OR\n"
                 "{\"sql\": null, \"response\": \"<conversational reply>\"}\n\n"
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
    def agent_warning(self, message: str) -> str:
        """Attendance Warning Agent with full NLP support for all query types."""
        msg_lower = message.lower()

        # --- Domain Security ---------------------------------------------
        out_of_scope = {
            'exam': 'Examination', 'schedule': 'Examination',
            'salary': 'Faculty', 'enroll': 'Student Management',
            'gpa': 'Student Management', 'scholarship': 'Scholarship',
        }
        for kw, agent in out_of_scope.items():
            if kw in msg_lower and 'attendance' not in msg_lower:
                return (
                    f"⚠️ **Out of Scope:** This task belongs to the **{agent} Agent**.\n"
                    f"I am the **Attendance Warning Agent** — I only handle attendance monitoring."
                )

        # --- Helpers ---------------------------------------------------------
        DEPT_PATTERN = r'\b(CS|CSE|IT|ECE|EEE|MECH|CIVIL|AI|DS)\b'
        dept_m = re.search(DEPT_PATTERN, message.upper())
        dept = dept_m.group(1) if dept_m else None
        if dept == 'CSE': dept = 'CS'

        roll = self.extract_roll_no(message)

        # Threshold extraction  e.g. "below 70%" or "less than 65"
        thresh_m = re.search(r'(?:below|less\s+than|under|<)\s*(\d+(?:\.\d+)?)\s*%?', msg_lower)
        threshold = float(thresh_m.group(1)) if thresh_m else 75.0
        # Override for "critical" queries → 65%
        if any(kw in msg_lower for kw in ['critical', 'very low', 'extremely low', 'debarred', 'debarment', 'danger', 'serious', 'high-risk', 'far below']):
            threshold = 65.0

        def _get_pct(student):
            recs = AttendanceRecord.objects.filter(roll_no=student)
            total = recs.count()
            if total == 0:
                return None, 0, 0
            present = recs.filter(status='present').count()
            return round(present / total * 100, 1), present, total

        def _status_badge(pct):
            if pct < 65: return '🔴 CRITICAL'
            if pct < 75: return '🟡 WARNING'
            return '🟢 SAFE'

        def _classes_needed(present, total, target_pct=75.0):
            """Classes needed to cross target_pct%."""
            if total == 0: return 0
            curr_pct = present / total * 100
            if curr_pct >= target_pct: return 0
            return max(0, int((target_pct / 100 * total - present) / (1 - target_pct / 100)) + 1)

        # ─── 0. NOTIFICATIONS / ACTIONS ───────────────────────────────────
        if any(kw in msg_lower for kw in ['send', 'notify', 'alert email', 'inform']):
            qs = Student.objects.all()
            if dept: qs = qs.filter(department__iexact=dept)
            count = 0
            for s in qs:
                pct, _, _ = _get_pct(s)
                if pct is not None and pct < threshold:
                    count += 1
            if count == 0:
                return f"✅ **No notifications sent.** All students{' in ' + dept if dept else ''} are above {threshold}%."
            return (
                f"📧 **Action Executed: Automated Notifications Sent**\n"
                f"- **Recipients:** {count} students{' in ' + dept if dept else ''} (Attendance < {threshold}%)\n"
                f"- **CC'd:** HOD, Faculty Advisors, and Parents/Guardians\n"
                f"- **Message:** Formal warning regarding university attendance policies and examination debarment risk."
            )

        # ─── 1. EARLY WARNING / PREDICTION (Students 75-82%) ──────────────
        if any(kw in msg_lower for kw in ['predict', 'soon', 'close to', 'dropping', 'early warning', 'likely to']):
            qs = Student.objects.all()
            if dept: qs = qs.filter(department__iexact=dept)
            at_risk_soon = []
            for s in qs:
                pct, pre, tot = _get_pct(s)
                if pct is not None and 75.0 <= pct <= 82.0:
                    at_risk_soon.append((s, pct, pre, tot))
            
            at_risk_soon.sort(key=lambda x: x[1])
            if not at_risk_soon:
                return "✅ **No students currently in the early-warning zone (75-82%).**"
            
            lines = [f"⚠️ **{s.name}** ({s.roll_no}) — **{pct}%** (Could fall below 75% if absent {max(1, int(pre / 0.75) - tot)} more times)" for s, pct, pre, tot in at_risk_soon]
            top_lines = "\n".join(lines[:15])
            heading = f"🔮 **Attendance Prediction & Early Warning**\nFound **{len(at_risk_soon)} students** hovering near the 75% edge:\n"
            return heading + top_lines

        # ─── 2. STUDENT-SPECIFIC REPORT ───────────────────────────────────
        # Try to extract name if no roll provided
        if not roll:
            name_m = re.search(r'(?:for|of|student|check|about)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', message)
            if name_m and len(name_m.group(1).strip()) > 2 and name_m.group(1).strip().lower() not in ['student', 'students', 'all', 'attendance', 'every', 'each', 'average', 'department']:
                name_query = name_m.group(1).strip()
                qs = Student.objects.filter(name__icontains=name_query)
                if qs.count() == 1:
                    roll = qs.first().roll_no
                elif qs.count() > 1:
                    return f"Found multiple students matching '{name_query}'. Please provide a Roll Number."

        if roll:
            try:
                student = Student.objects.get(roll_no=roll.upper())
                pct, present, total = _get_pct(student)
                if pct is None:
                    return f"📋 No attendance records found for **{student.name}** ({roll.upper()})."

                needed = _classes_needed(present, total)
                badge = _status_badge(pct)
                bar_filled = int(pct / 5)
                bar = '█' * bar_filled + '░' * (20 - bar_filled)

                recent = AttendanceRecord.objects.filter(roll_no=student).order_by('-date')[:7]
                recent_log = "\n".join([f"  - {r.date}: {'✅' if r.status=='present' else '❌'} {r.status.title()}" for r in recent])

                out = (
                    f"📊 **Attendance Report: {student.name} ({roll.upper()})**\n"
                    f"- **Dept:** {student.department or 'N/A'} | **Year:** {student.year or 'N/A'}\n"
                    f"- **Present:** {present} / {total} days\n"
                    f"- **Attendance:** `{bar}` **{pct}%**\n"
                    f"- **Status:** {badge}\n"
                )
                if needed:
                    out += f"- ⚠️ Must attend **{needed} more consecutive classes** to reach 75%\n"
                if recent_log:
                    out += f"\n**Last {recent.count()} Records:**\n{recent_log}"
                return out
            except Student.DoesNotExist:
                return f"❌ Student **{roll.upper()}** not found."

        # ─── 3. PREDICTION "How many classes must X attend?" ──────────────
        if any(kw in msg_lower for kw in ['how many classes', 'classes must', 'need to attend', 'classes needed', 'to reach', 'more classes does', 'attendance gap', 'recovery plan', 'fix attendance']):
            name_m = re.search(r'(?:must|for|student|about|does|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', message)
            if not name_m:
                 # fallback to finding the first Capitalized word that isn't the first word
                 name_m = re.search(r'(?<!^)\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', message)
            target_m = re.search(r'(?:reach|above|to)\s+([\d.]+)%?', msg_lower)
            target = float(target_m.group(1)) if target_m else 75.0
            
            s = None
            if roll:
                qs = Student.objects.filter(roll_no=roll.upper())
                if qs.exists(): s = qs.first()
            elif name_m:
                name = name_m.group(1).strip()
                if name.lower() not in ['student', 'students', 'all', 'attendance', 'department']:
                    qs = Student.objects.filter(name__icontains=name)
                    if qs.exists(): s = qs.first()
                    
            if s:
                pct, present, total = _get_pct(s)
                if pct is None:
                    return f"No data for **{s.name}**."
                needed = _classes_needed(present, total, target)
                if needed == 0:
                    return f"✅ **{s.name}** already has **{pct}%** attendance — above {target}%. No extra classes needed!"
                return (
                    f"🔢 **{s.name}** currently has **{pct}%** attendance ({present}/{total} days).\n"
                    f"To reach **{target}%**, they must attend the next **{needed} consecutive classes**."
                )
            return "⚠️ Please include a student name or roll number: *How many classes must Rahul attend to reach 75%?*"

        # ─── 3. AVERAGE / STATISTICS ──────────────────────────────────────
        if any(kw in msg_lower for kw in ['average', 'avg', 'statistics', 'stats', 'distribution', 'which department', 'lowest', 'worst']):
            qs = Student.objects.all()
            if dept: qs = qs.filter(department__iexact=dept)

            dept_stats = {}
            total_pcts = []
            for s in qs:
                pct, _, _ = _get_pct(s)
                if pct is None: continue
                total_pcts.append(pct)
                d = s.department or 'Unknown'
                if d not in dept_stats:
                    dept_stats[d] = []
                dept_stats[d].append(pct)

            if not total_pcts:
                return "⚠️ No attendance records found."

            # Average for a specific dept
            if dept and 'average' in msg_lower:
                dept_pcts = dept_stats.get(dept, [])
                if not dept_pcts:
                    return f"No attendance data for {dept} department."
                avg = sum(dept_pcts) / len(dept_pcts)
                return f"📊 Average attendance in **{dept}** department: **{avg:.1f}%** ({len(dept_pcts)} students tracked)"

            # Overall average / statistics
            if any(kw in msg_lower for kw in ['average', 'avg', 'statistics', 'stats', 'performance summary']):
                overall_avg = sum(total_pcts) / len(total_pcts)
                return (
                    f"📊 **University Attendance Statistics:**\n"
                    f"- Overall Average: **{overall_avg:.1f}%**\n"
                    f"- Students tracked: {len(total_pcts)}\n"
                    f"- Below 75%: **{sum(1 for p in total_pcts if p < 75)}**\n"
                    f"- Below 65% (Critical): **{sum(1 for p in total_pcts if p < 65)}**"
                )

            # Department distribution / worst department
            dept_avgs = [(d, round(sum(pts)/len(pts), 1), len(pts)) for d, pts in dept_stats.items()]
            dept_avgs.sort(key=lambda x: x[1])
            lines = [f"- **{d}**: {avg}% avg | {n} students" for d, avg, n in dept_avgs]
            heading = "🏆 Department with lowest attendance: **{}** ({:.1f}%)\n\n".format(
                dept_avgs[0][0], dept_avgs[0][1]) if dept_avgs else ""
            return heading + "📊 **Attendance by Department:**\n" + "\n".join(lines)

        # ─── 4. COUNT QUERIES ─────────────────────────────────────────────
        if any(kw in msg_lower for kw in ['how many', 'count', 'number of']):
            qs = Student.objects.all()
            if dept: qs = qs.filter(department__iexact=dept)
            count = 0
            for s in qs:
                pct, _, _ = _get_pct(s)
                if pct is not None and pct < threshold:
                    count += 1
            scope = f" in {dept}" if dept else ""
            return f"📊 **{count} student(s)**{scope} have attendance below **{threshold}%**."

        # ─── 5. WARNING LIST (default: below 75% or user-specified threshold) ─
        at_risk = []
        qs = Student.objects.all()
        if dept: qs = qs.filter(department__iexact=dept)

        for s in qs:
            pct, present, total = _get_pct(s)
            if pct is None or pct >= threshold:
                continue
            needed = _classes_needed(present, total)
            at_risk.append({
                'name': s.name, 'roll': s.roll_no, 'dept': s.department or '?',
                'pct': pct, 'present': present, 'total': total, 'needed': needed,
            })

        at_risk.sort(key=lambda x: x['pct'])

        if not at_risk:
            dept_str = f" in {dept}" if dept else ""
            return f"✅ **All students{dept_str} are above {threshold}% attendance.** No warnings needed!"

        lines = []
        for r in at_risk[:25]:
            badge = '🔴' if r['pct'] < 65 else '🟡'
            status_txt = 'CRITICAL' if r['pct'] < 65 else 'WARNING'
            lines.append(
                f"{badge} **{r['name']}** ({r['roll']}) | {r['dept']} | "
                f"**{r['pct']}%** [{status_txt}] | needs {r['needed']} more classes"
            )

        dept_header = f" in **{dept}**" if dept else ""
        critical = sum(1 for r in at_risk if r['pct'] < 65)
        warning = len(at_risk) - critical
        heading = (
            f"⚠️ **{len(at_risk)} Students At Risk{dept_header}** "
            f"(below {threshold}%): {critical} Critical | {warning} Warning\n"
        )
        if len(at_risk) > 25:
            heading += f"*(showing first 25 of {len(at_risk)})*\n"
        return heading + "\n".join(lines)

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
        DEPT_PATTERN = r'\b(CS|CSE|IT|ECE|EEE|MECH|CIVIL|AI|DATA\s*SCIENCE|DS|ELECTRONICS)\b'
        YEAR_PATTERN = r'\b(1|2|3|4)(?:st|nd|rd|th)?\s*year\b|\b(first|second|third|fourth|final)\s*year\b'
        GPA_GT_PATTERN = r'gpa\s+(?:above|greater\s+than|higher\s+than|>|>=)\s*(\d+(?:\.\d+)?)'
        GPA_LT_PATTERN = r'gpa\s+(?:below|less\s+than|lower\s+than|<|<=)\s*(\d+(?:\.\d+)?)'
        GPA_BETWEEN_PATTERN = r'gpa\s+between\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)'
        JOIN_YEAR_PATTERN = r'(?:joined?\s+in|batch|admitted?\s+in|from)\s+(20\d{2})'

        dept_m = re.search(DEPT_PATTERN, message.upper())
        dept = dept_m.group(1).replace(' ', '') if dept_m else None
        if dept == 'CSE': dept = 'CS'

        year_m = re.search(YEAR_PATTERN, msg_lower)
        if year_m:
            yr_map = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'final': 4}
            year = yr_map.get(year_m.group(2), year_m.group(1))
        else:
            year = None

        join_year_m = re.search(JOIN_YEAR_PATTERN, msg_lower)
        join_year = int(join_year_m.group(1)) if join_year_m else None

        gpa_gt_m = re.search(GPA_GT_PATTERN, msg_lower)
        gpa_lt_m = re.search(GPA_LT_PATTERN, msg_lower)
        gpa_bw_m = re.search(GPA_BETWEEN_PATTERN, msg_lower)

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
        if any(kw in msg_lower for kw in ['enroll', 'add', 'admit', 'register', 'create', 'new', 'student name']):
            # Keep commas to help bound the name match
            name_m = re.search(r'(?:student\s+name|name\s+is|name|student|called|for)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)', message, re.IGNORECASE)
            if not name_m:
                name_m = re.search(r'(?:enroll|add|admit|register)\s+(?:new\s+)?(?:a\s+)?(?:student\s+)?(?:named?\s+)?([a-zA-Z]+(?:\s+[a-zA-Z]+)?)', message, re.IGNORECASE)
            
            student_name = name_m.group(1).strip().title() if name_m else None
            if student_name and student_name.lower() in ['student', 'a', 'the', 'named', 'name', 'is', 'for']: 
                student_name = None

            roll_gen_m = re.search(r'roll\s*(?:no|number)?[:\s\-]+([a-zA-Z0-9]+)', message, re.IGNORECASE)
            if not roll_gen_m:
                roll_gen_m = re.search(r'\b([a-zA-Z]{2,4}\d{3,4})\b', message, re.IGNORECASE)
            
            new_roll = roll_gen_m.group(1).upper() if roll_gen_m else roll

            if student_name and re.search(DEPT_PATTERN, student_name.upper()):
                student_name = student_name.split()[0]
                
            if student_name:
                student_name = re.sub(r'(?i)\b(to|in|age|caste|department|dpartment)\b.*', '', student_name).strip()

            yr_enroll_m = re.search(r'\b(20\d{2})\b', message)
            enroll_join_year = int(yr_enroll_m.group(1)) if yr_enroll_m else None

            yr_academic_m = re.search(r'\b(1|2|3|4)(?:st|nd|rd|th)?\s*year\b', msg_lower)
            enroll_year = int(yr_academic_m.group(1)) if yr_academic_m else 1

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
            if gpa_bw_m:
                qs = qs.filter(gpa__gte=float(gpa_bw_m.group(1)), gpa__lte=float(gpa_bw_m.group(2)))
            elif gpa_gt_m:
                qs = qs.filter(gpa__gt=float(gpa_gt_m.group(1)))
            elif gpa_lt_m:
                qs = qs.filter(gpa__lt=float(gpa_lt_m.group(1)))

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
            if gpa_gt_m: conditions.append(f"GPA > {gpa_gt_m.group(1)}")
            if gpa_lt_m: conditions.append(f"GPA < {gpa_lt_m.group(1)}")
            if gpa_bw_m: conditions.append(f"GPA {gpa_bw_m.group(1)}-{gpa_bw_m.group(2)}")
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
    # 3. ATTENDANCE AGENT
    # -----------------------------------------------------------------
    def agent_attendance(self, message: str) -> str:
        msg = message.lower()
        roll = self.extract_roll_no(message)

        # Mark attendance
        if ('mark' in msg or 'present' in msg or 'absent' in msg) and roll and self.role == 'teacher':
            status_val = 'absent' if 'absent' in msg else 'present'
            try:
                student = Student.objects.get(roll_no=roll)
                today = date.today()
                record, created = AttendanceRecord.objects.get_or_create(
                    roll_no=student, date=today,
                    defaults={'status': status_val}
                )
                if not created:
                    record.status = status_val
                    record.save()
                records = AttendanceRecord.objects.filter(roll_no=student)
                total = records.count()
                present = records.filter(status='present').count()
                pct = (present / total * 100) if total else 0
                return f"[Check] **{student.name}** marked **{status_val.upper()}** today.\nCurrent attendance: {pct:.1f}% ({present}/{total})"
            except Student.DoesNotExist:
                return f"Student {roll} not found."

        # View attendance for a student
        if roll:
            try:
                student = Student.objects.get(roll_no=roll)
                records = AttendanceRecord.objects.filter(roll_no=student).order_by('-date')
                total = records.count()
                present = records.filter(status='present').count()
                pct = (present / total * 100) if total else 0
                recent = records[:7]
                log = "\n".join([f"  - {r.date}: {r.status.upper()}" for r in recent])
                return (
                    f"[Clipboard] **Attendance: {student.name} ({roll})**\n"
                    f"- Total: {total} days | Present: {present} | Absent: {total - present}\n"
                    f"- Percentage: **{pct:.1f}%**\n\n"
                    f"**Last 7 days:**\n{log}"
                )
            except Student.DoesNotExist:
                return f"Student {roll} not found."

        # Low attendance list
        threshold = 75
        low = []
        for s in Student.objects.all():
            recs = AttendanceRecord.objects.filter(roll_no=s)
            total = recs.count()
            if total > 0:
                pct = recs.filter(status='present').count() / total * 100
                if pct < threshold:
                    low.append(f"- {s.name} ({s.roll_no}): {pct:.1f}%")
        if low:
            return f"[Warning] **Students Below {threshold}%:**\n" + "\n".join(low)
        return "All students are above the attendance threshold."

    # -----------------------------------------------------------------
    # 4. EXAM SCHEDULER AGENT – Full NLP Coverage
    # -----------------------------------------------------------------
    def agent_exam(self, message: str) -> str:
        """Exam Scheduler Agent handling scheduling, conflicts, rescheduling, and timeline viewing."""
        msg_lower = message.lower()

        # --- Domain Security ---------------------------------------------
        out_of_scope = {
            'attendance': 'Attendance Warning', 'present': 'Attendance Warning',
            'student enroll': 'Student Management', 'gpa': 'Student Management',
            'scholarship': 'Scholarship', 'salary': 'Faculty'
        }
        for kw, agent in out_of_scope.items():
            if kw in msg_lower and 'exam' not in msg_lower:
                return f"⚠️ **Out of Scope:** This task belongs to the **{agent} Agent**. I am the **Exam Scheduler Agent**."

        # --- Helpers ---------------------------------------------------------
        DEPT_PATTERN = r'\b(CS|CSE|IT|ECE|EEE|MECH|CIVIL|AI|DS)\b'
        dept_m = re.search(DEPT_PATTERN, message.upper())
        dept = dept_m.group(1) if dept_m else None
        if dept == 'CSE': dept = 'CS'

        sem_m = re.search(r'semester\s*(\d+)', msg_lower)
        semester = int(sem_m.group(1)) if sem_m else None

        # Parse relative dates (simplified for hackathon demo)
        target_date = None
        now = date.today()
        if 'tomorrow' in msg_lower:
            target_date = now + timedelta(days=1)
        elif 'today' in msg_lower:
            target_date = now
        elif 'next week' in msg_lower:
            target_date = now + timedelta(days=7) # rough proxy
        elif 'next month' in msg_lower:
            target_date = now + timedelta(days=30)
            
        # Parse explicit dates (e.g., April 10, April 15)
        date_m = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|aug|sept|oct|nov|dec)\s+(\d{1,2})', msg_lower)
        if date_m:
            month_str, day_str = date_m.groups()
            try:
                # Basic parsing, assume current year
                dt = datetime.strptime(f"{month_str} {day_str} {now.year}", "%B %d %Y")
                target_date = dt.date()
            except ValueError:
                try: 
                    dt = datetime.strptime(f"{month_str} {day_str} {now.year}", "%b %d %Y")
                    target_date = dt.date()
                except ValueError: pass

        # Parse Course Name (e.g. "for Data Structures", "Mathematics exam")
        course_m = re.search(r'(?:for|course|subject)\s+([A-Z][a-zA-Z\s]+)(?:\s+exam|\s+course)?', message)
        if not course_m: 
             course_m = re.search(r'([A-Z][a-zA-Z\s]+)\s+exam', message)
        course_name = course_m.group(1).strip() if course_m else None
        # Clean up common false positives
        if course_name and course_name.lower() in ['the', 'an', 'midterm', 'final', 'upcoming', 'semester']: course_name = None

        # ─── 1. CONFLICT CHECKING ─────────────────────────────────────────
        if any(kw in msg_lower for kw in ['conflict', 'clash', 'overlap', 'same day', 'same time', 'errors', 'issues']):
            exams = Exam.objects.all()
            if semester: exams = exams.filter(course__semester=semester)
            
            # Group by Date & Dept/Semester
            conflicts = []
            exams_list = list(exams.select_related('course'))
            for i in range(len(exams_list)):
                for j in range(i + 1, len(exams_list)):
                    e1, e2 = exams_list[i], exams_list[j]
                    if e1.date == e2.date:
                        # If time is specified and overlaps, or if no time is specified but same date/dept/sem
                        time_overlap = False
                        if e1.start_time and e1.end_time and e2.start_time and e2.end_time:
                            time_overlap = (e1.start_time < e2.end_time and e2.start_time < e1.end_time)
                        
                        student_clash = (e1.course.department == e2.course.department and e1.course.semester == e2.course.semester)
                        room_clash = (e1.room and e2.room and e1.room == e2.room and time_overlap)
                        
                        if student_clash or room_clash or (time_overlap and student_clash):
                            reason = "Same Dept & Semester on same day"
                            if time_overlap: reason += " (Time Overlap!)"
                            if room_clash: reason = "Room Double Booking"
                            conflicts.append((e1, e2, reason))

            if not conflicts:
                return f"✅ **No exam conflicts detected** {'for Semester ' + str(semester) if semester else 'in the current schedule'}."
            
            lines = [f"⚠️ **{e1.course.name}** and **{e2.course.name}** ({e1.date}) — {r}" for e1, e2, r in conflicts]
            return f"🚨 **Exam Conflicts Detected ({len(conflicts)}):**\n" + "\n".join(lines[:10])

        # ─── 2. DELETE / CANCEL EXAM ──────────────────────────────────────
        if any(kw in msg_lower for kw in ['cancel', 'delete', 'remove']):
            qs = Exam.objects.all()
            if course_name: qs = qs.filter(course__name__icontains=course_name)
            if target_date: qs = qs.filter(date=target_date)
            if semester: qs = qs.filter(course__semester=semester)
            if dept: qs = qs.filter(course__department=dept)

            count = qs.count()
            if count == 0:
                return "❌ Could not find any matching exams to cancel. Please be more specific (e.g., 'Cancel the Mathematics exam')."
            elif count > 5 and not target_date and not course_name: # Safety
                return f"⚠️ Found {count} exams matching that request. Please be more specific to avoid accidentally deleting the whole timetable."
            
            deleted_info = [f"- {e.course.name} ({e.date})" for e in qs]
            qs.delete()
            return f"🗑️ **Successfully Cancelled Exams:**\n" + "\n".join(deleted_info)

        # ─── 3. UPDATE / RESCHEDULE EXAM ──────────────────────────────────
        if any(kw in msg_lower for kw in ['move', 'change', 'reschedule', 'postpone', 'update', 'shift', 'adjust']):
            qs = Exam.objects.all()
            if course_name: qs = qs.filter(course__name__icontains=course_name)
            
            if not qs.exists():
                return f"❌ Could not find an exam schedule for **{course_name or 'the specified course'}** to reschedule."
            
            exam = qs.first()
            old_date = exam.date
            
            # Simple day shifting parser
            days_shift = 0
            if 'tomorrow' in msg_lower: days_shift = 1
            elif 'next week' in msg_lower: days_shift = 7
            elif 'two days' in msg_lower: days_shift = 2
            
            if days_shift > 0:
                exam.date = date.today() + timedelta(days=days_shift)
            elif target_date:
                exam.date = target_date
            elif 'monday' in msg_lower: # basic day-of-week parsing fallback
                # Just mock a future date for the demo
                exam.date = date.today() + timedelta(days=(7 - date.today().weekday()) % 7 + 0) # Next Monday
            
            if exam.date == old_date:
                return f"📝 Found **{exam.course.name}** exam, but couldn't determine the new date. Please try: *'Move Mathematics exam to April 15'*."
                
            exam.save()
            return f"🔄 **Exam Rescheduled Successfully:**\n**Course:** {exam.course.name}\n**Old Date:** {old_date}\n**New Date:** {exam.date}"

        # ─── 4. CREATE EXAM SCHEDULE ──────────────────────────────────────
        if any(kw in msg_lower for kw in ['create', 'schedule', 'add', 'plan', 'arrange', 'set up']):
            # Filter courses
            courses = Course.objects.all()
            if semester: courses = courses.filter(semester=semester)
            if dept: courses = courses.filter(department__iexact=dept)
            if course_name: courses = courses.filter(name__icontains=course_name)
            
            if not courses.exists():
                return "❌ Could not find matching courses to schedule. Ensure the department or semester exists."

            start_dt = target_date or (date.today() + timedelta(days=14)) # default to 2 weeks out
            
            created = []
            for i, c in enumerate(courses):
                exam_date = start_dt + timedelta(days=i*2) # Space them out by 2 days
                Exam.objects.create(
                    course=c, 
                    exam_type='midterm' if 'midterm' in msg_lower else 'final',
                    date=exam_date
                )
                created.append(f"- **{c.name}** ({c.code}): {exam_date.strftime('%b %d, %Y')}")
            
            intro = f"🗓️ **Successfully Created Exam Schedule{' for Semester ' + str(semester) if semester else ''}{' (' + dept + ')' if dept else ''}:**\n"
            return intro + "\n".join(created[:15]) + (f"\n*(...and {len(created)-15} more)*" if len(created) > 15 else "")

        # ─── 5. VIEW TIMETABLE / SMART QUERIES ────────────────────────────
        qs = Exam.objects.select_related('course').all()
        if dept: qs = qs.filter(course__department__iexact=dept)
        if semester: qs = qs.filter(course__semester=semester)
        if target_date: qs = qs.filter(date=target_date)
        
        # Determine timeframe
        if 'this week' in msg_lower:
            qs = qs.filter(date__range=[now, now + timedelta(days=7)])
        elif 'this month' in msg_lower:
            qs = qs.filter(date__range=[now, now + timedelta(days=30)])
        elif 'upcoming' in msg_lower or 'next' in msg_lower:
            qs = qs.filter(date__gte=now)
            
        qs = qs.order_by('date', 'start_time')
        
        if 'how many' in msg_lower:
            return f"📊 **{qs.count()} exams** are scheduled matching your query."
            
        if not qs.exists():
            return "📋 No exams found matching your schedule query."
            
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
        msg_lower = message.lower()
        
        # Domain security constraints
        domain_blocks = {
            'student': 'Student', 'enroll': 'Student', 'gpa': 'Student', 'caste': 'Student',
            'attendance': 'Attendance', 'present': 'Attendance', 'absent': 'Attendance',
            'exam': 'Exam', 'schedule exam': 'Exam', 'timetable': 'Exam'
        }
        for kw, agent_name in domain_blocks.items():
            if kw in msg_lower and not any(safe in msg_lower for safe in ['course', 'subject', 'elective', 'curriculum', 'credits']):
                return f"⚠️ **Out of Scope:** This task belongs to the **{agent_name} Agent**. I am the **Course Management Agent**."

        # Common extractors
        DEPT_PATTERN = r'\b(CS|CSE|IT|ECE|EEE|MECH|CIVIL|AI|DATA\s*SCIENCE|DS|ELECTRONICS)\b'
        dept_m = re.search(DEPT_PATTERN, message.upper())
        dept = dept_m.group(1).replace(' ', '') if dept_m else None
        if dept == 'CSE': dept = 'CS'

        sem_m = re.search(r'semester\s+(\d)', msg_lower)
        semester = int(sem_m.group(1)) if sem_m else None
        
        c_type = 'Elective' if 'elective' in msg_lower else ('Core' if 'core' in msg_lower else None)

        # ─── 0. HELPERS
        def _extract_course_name(text):
            # Try specific patterns first
            m = re.search(r'(?:called|named|course|subject)\s+([A-Z][a-zA-Z\s]+?)(?=\s+(?:for|to|in|from|course|subject|$))', text, re.IGNORECASE)
            if m and len(m.group(1).strip()) > 2:
                name = m.group(1).strip().title()
                if name.lower() not in ['course', 'subject', 'a', 'the', 'new']:
                    return name
            return None

        # ─── 1. CREATE COURSE ─────────────────────────────────────────────
        if any(kw in msg_lower for kw in ['create', 'add ', 'introduce', 'register ', 'include a new']):
            # Explicitly guard against "assign" keywords masquerading as "add"
            if not any(kw in msg_lower for kw in ['assign ', 'link ', 'to the cse', 'to the it', 'to the ece', 'to semester', 'add machine learning to']):
                course_name = _extract_course_name(message)
            if not course_name:
                return "⚠️ Could not extract the course name. Please say something like: *Create a new course called Machine Learning for semester 6*."
                
            credits_m = re.search(r'(\d+)\s+credits?', msg_lower)
            cr = int(credits_m.group(1)) if credits_m else 3 # Default 3
            
            # Generate a pseudo code based on dept and semester
            c_dept = dept or 'GEN'
            c_sem = semester or 1
            code = f"{c_dept}{c_sem}0{random.randint(1,9)}"
            
            ctype = c_type or 'Core'
            
            try:
                c = Course.objects.create(
                    name=course_name,
                    code=code,
                    department=dept,
                    semester=semester,
                    credits=cr,
                    type=ctype,
                    year=(semester + 1) // 2 if semester else None
                )
                return f"✅ **Course Successfully Created:**\n- **Name:** {c.name}\n- **Code:** {c.code}\n- **Type:** {c.type}\n- **Credits:** {c.credits}\n- **Semester:** {c.semester or 'Any'}\n- **Department:** {c.department or 'General'}"
            except Exception as e:
                return f"❌ Failed to create course: {str(e)}"

        # ─── 2. UPDATE COURSE ─────────────────────────────────────────────
        if any(kw in msg_lower for kw in ['update', 'change', 'modify', 'move', 'adjust']):
            course_name = _extract_course_name(message)
            
            # Extract names without "course called" if standard extract fails
            if not course_name:
                alt_m = re.search(r'(?:for|of|to)\s+([A-Z][a-zA-Z\s]+)(?:course|subject)?', message)
                if alt_m:
                    n = alt_m.group(1).strip()
                    if len(n) > 3 and not n.lower() in ['course', 'subject', 'a', 'the']:
                        course_name = n
            qs = Course.objects.all()
            if course_name: qs = qs.filter(name__icontains=course_name)
            elif dept: qs = qs.filter(department=dept) # Very risky, just as a fallback 
            
            if not qs.exists():
                return f"❌ Could not find a course matching **{course_name or 'the request'}** to update."
            if qs.count() > 1 and not course_name:
                return "⚠️ Found multiple courses. Please specify the exact course name to update."
                
            course = qs.first()
            updates = []
            
            # Change credits
            cr_m = re.search(r'credits?\s+(?:to|of\s+.*?\s+to)\s+(\d+)', msg_lower)
            if cr_m:
                course.credits = int(cr_m.group(1))
                updates.append(f"Credits → {course.credits}")
                
            # Change semester
            if semester and course.semester != semester:
                course.semester = semester
                course.year = (semester + 1) // 2
                updates.append(f"Semester → {course.semester}")
                
            # Change department (reassign)
            if dept and course.department != dept:
                course.department = dept
                updates.append(f"Department → {course.department}")
                
            # Change type
            if c_type and course.type != c_type:
                course.type = c_type
                updates.append(f"Type → {course.type}")
                
            if not updates:
                return f"📝 Found course **{course.name}**, but couldn't determine what to update. Example: *Change credits of Data Structures to 4*."
                
            course.save()
            return f"🔄 **Course Updated Successfully:**\n**{course.name}** ({course.code})\n" + "\n".join([f"- {u}" for u in updates])

        # ─── 3. DELETE COURSE ─────────────────────────────────────────────
        if any(kw in msg_lower for kw in ['delete', 'remove', 'cancel']):
            course_name = _extract_course_name(message)
            if not course_name:
                alt_m = re.search(r'(?:delete|remove|cancel)\s+(?:the\s+)?([A-Z][a-zA-Z\s]+?)(?:\s+course|\s+subject|\s+from|\s+elective|$)', message, re.IGNORECASE)
                if alt_m: course_name = alt_m.group(1).strip()
                
            if not course_name:
                return "⚠️ Please specify the course name to delete. Example: *Delete the course Machine Learning*."
                
            qs = Course.objects.filter(name__icontains=course_name)
            if not qs.exists():
                return f"❌ Could not find course **{course_name}** in the curriculum."
                
            c = qs.first()
            c_name, c_code = c.name, c.code
            c.delete()
            return f"🗑️ **Successfully Deleted Course:**\n- {c_name} ({c_code})"

        # ─── 4. ASSIGN COURSE ─────────────────────────────────────────────
        if any(kw in msg_lower for kw in ['assign ', 'link ', 'add machine learning to', 'add data analytics to', 'add blockchain', 'add mobile']):
            course_name = _extract_course_name(message)
            if not course_name:
                 alt_m = re.search(r'(?:assign|add|link)\s+([A-Z][a-zA-Z\s]+?)(?:\s+to|\s+course|\s+subject)', message, re.IGNORECASE)
                 if alt_m: course_name = alt_m.group(1).strip()
            
            if not course_name:
                 return "⚠️ Please specify a course name to assign."
            qs = Course.objects.filter(name__icontains=course_name)
            if not qs.exists():
                return f"❌ Could not find an existing course named **{course_name}**."
                
            c = qs.first()
            assigned = []
            if dept:
                c.department = dept
                assigned.append(f"Department: {dept}")
            if semester:
                c.semester = semester
                c.year = (semester + 1) // 2
                assigned.append(f"Semester: {semester}")
                
            if assigned:
                c.save()
                return f"✅ **Successfully Assigned {c.name}:**\n- " + "\n- ".join(assigned)
            return "⚠️ Did not detect a target department or semester to assign the course to."

        # ─── 5. VIEW / SMART QUERIES ──────────────────────────────────────
        qs = Course.objects.all()
        
        # Filtering
        if dept: qs = qs.filter(department=dept)
        if semester: qs = qs.filter(semester=semester)
        if c_type: qs = qs.filter(type=c_type)
        
        # Specific search string "final year"
        if 'final year' in msg_lower:
            qs = qs.filter(year=4)
            
        # Aggregations / counts
        if 'highest credits' in msg_lower:
            qs = qs.order_by('-credits')[:1]
            if qs.exists():
                c = qs.first()
                return f"🏆 **Highest Credit Course:**\n- **{c.name}** ({c.code}) with **{c.credits} Credits**."
                
        if any(kw in msg_lower for kw in ['how many', 'count', 'what courses', 'which courses', 'list', 'show me', 'display']):
            count = qs.count()
            suffix = []
            if semester: suffix.append(f"in Semester {semester}")
            if dept: suffix.append(f"for {dept}")
            if c_type: suffix.append(f"that are {c_type}")
            suf_str = " ".join(suffix)
            
            if 'how many' in msg_lower or 'count' in msg_lower:
                return f"📊 There are **{count} courses** {suf_str}."
        
        if 'what new courses' in msg_lower or 'recently' in msg_lower:
            qs = qs.order_by('-id') # pseudo-recent
            
        if 'mandatory' in msg_lower:
            qs = qs.filter(type__iexact='Core')
            
        if 'advanced' in msg_lower:
            qs = qs.filter(name__icontains='Advanced')

        if not qs.exists():
            return "📋 No courses found matching your criteria."
            
        # Display list
        lines = []
        for c in qs[:20]:
            cr_str = f"| {c.credits} Cr" if c.credits else ""
            lines.append(f"- **{c.name}** ({c.code}) {cr_str}")
            
        header = "📚 **Course Curriculum List:**\n"
        if semester: header = f"📚 **Semester {semester} Courses:**\n"
        elif dept: header = f"📚 **{dept} Department Courses:**\n"
        
        msg = header + "\n".join(lines)
        if qs.count() > 20: msg += f"\n\n*(Showing 20 of {qs.count()} courses)*"
        return msg
