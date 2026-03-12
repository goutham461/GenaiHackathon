"""
Gemini-powered Agent Router (google.genai SDK)
8 domain-isolated agents with real DB actions.
"""
import re
import os
import json
import time
import logging
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
        'warning':    ['risk', 'safe', 'dropout', 'fail', 'low attendance', 'alert', 'warning'],
        'attendance': ['attendance', 'present', 'absent', 'percent', 'days', 'status', 'check'],
        'exam':        ['exam', 'marks', 'result', 'grade', 'rank', 'topper', 'schedule', 'table', 'midterm', 'final'],
        'faculty':    ['faculty', 'teacher', 'professor', 'prof.', 'workload', 'staff', 'department head', 'hod'],
        'letter':     ['letter', 'permission', 'bonafide', 'noc', 'internship', 'hackathon', 'certificate', 'request'],
        'analytics':  ['stats', 'analytics', 'trend', 'report', 'overall', 'campus', 'dashboard'],
        'student':    ['enroll', 'delete', 'remove', 'register', 'list students', 'show students', 'all students', 'new student'],
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
        }

        if domain and domain in dispatch:
            return dispatch[domain](message)

        # FAST-PASS: Handle common conversational queries locally to save Gemini quota
        local_reply = self._local_conversational_reply(msg_lower)
        if local_reply:
            return local_reply

        # Fall back to Gemini for general Q&A
        # Check if user explicitly disabled Gemini or we are in cooldown
        if getattr(settings, 'GEMINI_DISABLED', False):
             return self._fallback_help(message=message, quota_hit=True)

        return self._gemini_general(message)

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
        match = re.search(r'\b[A-Za-z]{2}\d{4}\b', text.upper())
        return match.group(0) if match else None

    # -----------------------------------------------------------------
    # Text-to-SQL-to-Text -- CampusAI Universal Query Engine
    # Uses a SINGLE Gemini call to generate SQL + response template together
    # to minimize API usage.
    # -----------------------------------------------------------------
    def _gemini_general(self, message: str) -> str:
        if not self.client:
            return self._fallback_help()

        # -- Actual Django SQLite table & column mapping ------------------
        schema = (
            "TABLE students_student: roll_no (PK/student_id), name, department, year, email, phone\n"
            "TABLE attendance_attendancerecord: id, roll_no (FK->students_student.roll_no), date, status ('present'/'absent')\n"
            "TABLE courses_course: id, course_name, faculty_name, department\n"
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
            wait_left = int(AgentRouter.QUOTA_COOLDOWN - (current_time - AgentRouter._last_429_time))
            return self._fallback_help(message=message, quota_hit=True)

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

        # If Gemini completely fails, try OpenAI fallback
        if not extracted and getattr(settings, 'OPENAI_API_KEY', None):
            print("[CampusAI] Gemini pool exhausted, trying OpenAI fallback...")
            openai_res = self._openai_fallback(combined_prompt)
            if openai_res:
                extracted = openai_res

        if not extracted:
            if last_err and ('quota' in last_err.lower() or '429' in last_err):
                AgentRouter._last_429_time = int(time.time()) # Global cooldown
                return self._fallback_help(message=message, quota_hit=True)
            return self._fallback_help(message=message)

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
    # 1. WARNING AGENT
    # -----------------------------------------------------------------
    def agent_warning(self, message: str) -> str:
        roll = self.extract_roll_no(message)
        if not roll:
            # List all at-risk students
            at_risk = []
            for s in Student.objects.all():
                records = AttendanceRecord.objects.filter(roll_no=s)
                total = records.count()
                if total > 0:
                    pct = records.filter(status='present').count() / total * 100
                    if pct < 75:
                        needed = int((0.75 * total - records.filter(status='present').count()) / 0.25) + 1
                        risk = "CRITICAL" if pct < 65 else "WARNING"
                        at_risk.append(f"- **{s.name}** ({s.roll_no}): {pct:.1f}% [{risk}] -- needs {needed} more days")
            if at_risk:
                return f"[Warning] **{len(at_risk)} Students At Risk:**\n" + "\n".join(at_risk)
            return "All students are above 75% attendance. No warnings."

        try:
            student = Student.objects.get(roll_no=roll)
            records = AttendanceRecord.objects.filter(roll_no=student)
            total = records.count()
            if total == 0:
                return f"No attendance records for {student.name} ({roll})."
            present = records.filter(status='present').count()
            pct = present / total * 100
            status = "CRITICAL RISK" if pct < 65 else "WARNING" if pct < 75 else "SAFE"
            emoji = "[Red Circle]" if pct < 65 else "[Yellow Circle]" if pct < 75 else "[Green Circle]"
            needed = max(0, int((0.75 * total - present) / 0.25) + 1) if pct < 75 else 0
            out = (
                f"{emoji} **Warning Report: {student.name} ({roll})**\n"
                f"- Department: {student.department}, Year {student.year}\n"
                f"- Present: {present}/{total} days\n"
                f"- Attendance: **{pct:.1f}%**\n"
                f"- Status: **{status}**\n"
            )
            if needed:
                out += f"- To reach 75%: attend **{needed} more consecutive days**\n"
                out += "Auto-alert would be sent to HOD and student's parent."
            return out
        except Student.DoesNotExist:
            return f"Student {roll} not found in database."

    # -----------------------------------------------------------------
    # 2. STUDENT AGENT
    # -----------------------------------------------------------------
    def agent_student(self, message: str) -> str:
        if self.role != 'teacher':
            return "Access Denied: Only teachers can manage student records."

        msg_lower = message.lower()
        if 'list' in msg_lower or 'show' in msg_lower:
            dept_match = re.search(r'\b(CS|IT|ECE|EEE|MECH)\b', message.upper())
            dept = dept_match.group(0) if dept_match else None
            qs = Student.objects.filter(department=dept) if dept else Student.objects.all()
            total = qs.count()
            students = qs[:10]
            if not students: return "No students found."
            lines = [f"- **{s.name}** ({s.roll_no}) | {s.department} Yr{s.year} | {s.email}" for s in students]
            return f"Students {'in ' + dept if dept else '(All)'} -- {total} total:**\n" + "\n".join(lines)

        # Regex-based entity extraction (no Gemini needed for structured commands)
        extracted = {}
        if 'enroll' in msg_lower or 'add' in msg_lower:
            extracted['action'] = 'enroll'
            # 1. Try to extract by comma-delimited segments first if present
            if ',' in message:
                segments = [s.strip() for s in message.split(',')]
                for seg in segments:
                    seg_l = seg.lower()
                    if 'name ' in seg_l or seg_l.endswith('name'):
                        pos = seg_l.rfind('name')
                        extracted['name'] = seg[pos+4:].strip().title()
                    if 'email' in seg_l:
                        m = re.search(r'[\w\.-]+@[\w\.-]+', seg)
                        if m: extracted['email'] = m.group(0)
                    if 'pass' in seg_l:
                        pos = seg_l.find('pass')
                        # skip 'password' too
                        offset = 8 if 'password' in seg_l else 4
                        extracted['password'] = seg[pos+offset:].strip()
                    if 'roll' in seg_l:
                        m = re.search(r'\b[A-Za-z]{2}\d{4}\b', seg.upper())
                        if m: extracted['roll_no'] = m.group(0)
                    if 'dept' in seg_l or 'department' in seg_l:
                        m = re.search(r'\b(CS|IT|ECE|EEE|MECH)\b', seg.upper())
                        if m: extracted['department'] = m.group(0)
                    if 'caste' in seg_l:
                        pos = seg_l.find('caste')
                        extracted['caste'] = seg[pos+5:].strip()
            
            # 2. Fallback or augment with individual regexes
            if not extracted.get('name'):
                name_match = re.search(r'(?:name|student)\s+([A-Za-z\s]{2,30})', message, re.IGNORECASE)
                if name_match:
                    raw = name_match.group(1).strip()
                    # If it contains "enroll", cleanup
                    extracted['name'] = re.sub(r'^(enroll|add|one|new|student)\s+', '', raw, flags=re.I).strip()
            
            if not extracted.get('email'):
                email_match = re.search(r'[\w\.-]+@[\w\.-]+', message)
                if email_match: extracted['email'] = email_match.group(0)
            
            if not extracted.get('roll_no'):
                roll_match = re.search(r'\b[A-Za-z]{2}\d{4}\b', message)
                if roll_match: extracted['roll_no'] = roll_match.group(0).upper()
            
            if not extracted.get('department'):
                dept_m = re.search(r'\b(CS|IT|ECE|EEE|MECH)\b', message.upper())
                if dept_m: extracted['department'] = dept_m.group(0)

            if not extracted.get('caste'):
                c_m = re.search(r'caste\s+([A-Za-z]+)', message, re.IGNORECASE)
                if c_m: extracted['caste'] = c_m.group(1).strip()
        elif 'delete' in msg_lower or 'remove' in msg_lower:
            extracted['action'] = 'delete'
            roll_match = re.search(r'\b[A-Za-z]{2}\d{4}\b', message)
            if roll_match: extracted['roll_no'] = roll_match.group(0).upper()


        action = extracted.get('action', 'unknown')
        if action == 'unknown':
            if 'enroll' in msg_lower or 'add' in msg_lower: action = 'enroll'
            elif 'delete' in msg_lower or 'remove' in msg_lower: action = 'delete'

        if action == 'enroll':
            name = extracted.get('name') or "New Student"
            roll = extracted.get('roll_no') or f"CS{__import__('random').randint(1000, 9999)}"
            email = extracted.get('email') or f"{roll.lower()}@student.edu"
            password = extracted.get('password') or "student123"
            dept = extracted.get('department') or "CS"
            caste = extracted.get('caste')

            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Create User Account (AbstractUser needs a username)
            user_obj, created_user = User.objects.get_or_create(email=email, defaults={
                'username': email,
                'full_name': name,
                'role': 'student'
            })
            if created_user:
                user_obj.set_password(password)
                user_obj.save()

            # Create Student Profile
            student, created_student = Student.objects.get_or_create(
                roll_no=roll.upper(),
                defaults={'name': name, 'department': dept, 'year': 1, 'email': email, 'caste': caste}
            )
            
            if created_student or created_user:
                return (f"[Check] **Student Successfully Enrolled!**\n\n"
                        f"- **Name:** {student.name}\n"
                        f"- **Roll No:** {student.roll_no}\n"
                        f"- **Email:** {email}\n"
                        f"- **Password:** `{password}`\n\n"
                        f"They can now log in to the student portal.")
            else:
                return f"[Info] Student {roll.upper()} or {email} already exists."

        if action == 'delete':
            roll = extracted.get('roll_no') or self.extract_roll_no(message)
            if roll:
                try:
                    s = Student.objects.get(roll_no=roll.upper())
                    name = s.name
                    email = s.email
                    s.delete()
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    User.objects.filter(email=email).delete()
                    return f"[Trash] **Deleted:** {name} ({roll.upper()}) and their auth account."
                except Student.DoesNotExist:
                    return f"Student {roll.upper()} not found."
            return "Format: *Delete [RollNo]*"

        return "Student Agent commands: 'add student [Name] email [Email] passed [Pass]' or 'Delete [RollNo]'"

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
    # 4. EXAM AGENT
    # -----------------------------------------------------------------
    def agent_exam(self, message: str) -> str:
        msg = message.lower()

        # Top students
        if 'top' in msg or 'rank' in msg or 'best' in msg:
            results = ExamResult.objects.select_related('roll_no', 'exam').order_by('-marks')[:10]
            if results:
                lines = [f"{i+1}. **{r.roll_no.name}** ({r.roll_no.roll_no}) -- {r.marks}% [{r.grade}] | {r.exam.course.name}" for i, r in enumerate(results)]
                return "[Trophy] **Top Students (Exam Results):**\n" + "\n".join(lines)
            return "No exam results found."

        # Upcoming exams
        upcoming = Exam.objects.filter(date__gte=date.today()).order_by('date').select_related('course', 'invigilator')
        if upcoming.exists():
            lines = [f"- **{e.course.name}** ({e.exam_type.title()}) -- {e.date} | Room: {e.room} | Invigilator: {e.invigilator.name}" for e in upcoming]
            return "[Books] **Upcoming Exams:**\n" + "\n".join(lines)
        return "No upcoming exams scheduled."

    # 5. FACULTY AGENT
    def agent_faculty(self, message: str) -> str:
        faculties = Faculty.objects.all()
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
            return f"Student {roll} not found."

    # -----------------------------------------------------------------
    # 7. LETTER AGENT
    # -----------------------------------------------------------------
    def agent_letter(self, message: str) -> str:
        roll = self.extract_roll_no(message)
        msg = message.lower()

        if not roll:
            # Show pending letters
            pending = Letter.objects.filter(status='pending').count()
            hod_approved = Letter.objects.filter(status='hod_approved').count()
            final = Letter.objects.filter(status='final_approved').count()
            return (
                f"[Scroll] **Letter Status Dashboard:**\n"
                f"- Pending HOD Approval: **{pending}**\n"
                f"- Pending Principal Approval: **{hod_approved}**\n"
                f"- Fully Approved: **{final}**\n\n"
                f"Use the Letters portal to manage approvals, or ask:\n"
                f"'*Generate bonafide for CS1001*'"
            )

        try:
            student = Student.objects.get(roll_no=roll)
            # Detect letter type from message
            letter_type = 'bonafide'
            if 'noc' in msg: letter_type = 'noc'
            elif 'internship' in msg: letter_type = 'internship'
            elif 'hackathon' in msg: letter_type = 'hackathon'
            elif 'academic' in msg: letter_type = 'academic'

            content = (
                f"To Whom It May Concern,\n\n"
                f"This is to certify that {student.name} (Roll: {roll}), "
                f"{student.department} Dept, Year {student.year}, has requested a {letter_type.upper()} letter.\n\n"
                f"Pending approval from HOD and Principal.\nDate: {date.today().strftime('%d %B %Y')}"
            )
            letter = Letter.objects.create(
                student_roll=student,
                requested_by=self.user,
                letter_type=letter_type,
                purpose=f"{letter_type.title()} for {student.name}",
                content=content,
                status='pending'
            )
            return (
                f"[Check] **Letter Request Created** (ID: #{letter.id})\n"
                f"- Student: {student.name} ({roll})\n"
                f"- Type: {letter_type.upper()}\n"
                f"- Status: [Hourglass] **Pending HOD Approval**\n\n"
                f"HOD can approve this in the *Letters Portal -- HOD Dashboard*."
            )
        except Student.DoesNotExist:
            return f"Student {roll} not found."

    # -----------------------------------------------------------------
    # 8. ANALYTICS AGENT
    # -----------------------------------------------------------------
    def agent_analytics(self, message: str) -> str:
        if self.role == 'student':
            return "Access Denied: Analytics is restricted to Teachers only."

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
            f"📊 **Campus Analytics Dashboard**\n\n"
            f"**Enrollment:**\n"
            f"- Total Students: {total_students}\n"
            f"- By Dept: {dept_line}\n"
            f"- Avg 12th Marks: {avg_marks:.1f}%\n\n"
            f"**Attendance:**\n"
            f"- Overall: {overall_att:.1f}%\n"
            f"- 🔴 High Risk: {high_risk} | 🟡 Medium: {medium_risk} | 🟢 Safe: {safe}\n\n"
            f"**Exam Performance:**\n"
            f"- Pass Rate: {pass_rate:.1f}% ({passing}/{results_total})"
        )
