import re
import json
import logging
from django.db import connection

logger = logging.getLogger(__name__)

class CampusAI:
    """
    Advanced CampusAI 24/7 Offline Engine.
    - Optimized with Pre-compiled Regex.
    - Context-Aware (Handles 'me', 'my', 'self').
    - Fuzzy Mapping for Depts.
    - Real-time Scholarship Eligibility Engine.
    """

    # --- Pre-compiled Patterns (Speed Optimization) ---
    PATTERNS = {
        'STUDENT_BY_ID': re.compile(r"(?:who\s+is|find|details?\s+of|name\s+of|student)\s+(?:me\s+)?(?:with\s+)?(?:id\s+)?(?P<id>[A-Z]+\d+)", re.I),
        'ATTENDANCE_QUERY': re.compile(r"(?:show|check|get|what\s+is)\s+(?:me\s+)?(?:the\s+)?attendance\s+(?:for|of|mine|my|me)?\s*(?P<id>[A-Z]+\d+)?", re.I),
        'LOW_ATTENDANCE': re.compile(r"(?:list|show|find|who\s+has)\s+(?:me\s+)?(?:the\s+)?(?:students\s+with\s+)?low\s+attendance(?:\s+below\s+(?P<limit>\d+))?", re.I),
        # Scholarship Expanded
        'SCHOLARSHIP_ELIGIBLE': re.compile(r"(?:am\s+i|which|list|check)\s+(?:me\s+)?(?:for\s+)?(?:any\s+)?(?:scholarship|scheme)s?\s*(?:i\s+am|me|my)?\s*(?:eligible|for)?", re.I),
        'SCHOLARSHIP_LIST': re.compile(r"(?:all|show|list|what\s+are)\s+(?:me\s+)?(?:the\s+)?(?:available|active)?\s*(?:scholarship|scheme)s?", re.I),
        # Faculty Expanded
        'FACULTY_DEPT': re.compile(r"(?:who|faculty|teachers|profs|list)\s+(?:me\s+)?(?:is|are|in|of|for)\s+(?P<dept>CS|IT|ECE|EEE|MECH|CIVIL|CHEM|PHY|MATH|BIO|ENG)", re.I),
        'FACULTY_LOAD': re.compile(r"(?:workload|courses|teaching|classes|subjects)\s+(?:me\s+)?(?:of|for)\s+(?P<name>[a-z\s\.]+)", re.I),
        # Exams Expanded
        'EXAM_SCHEDULE': re.compile(r"(?:upcoming|show|any|when\s+is|list)\s+(?:me\s+)?(?:the\s+)?(?P<subject>\w+)?\s*exams?", re.I),
        'TOP_STUDENTS': re.compile(r"(?:who\s+is|show|list|get|which)\s+(?:me\s+)?(?:the\s+)?(?:top|best|ranker|topper)s?\s*(?:students?)?", re.I),
        # Admin Expanded
        'ENROLL_STUDENT': re.compile(r"(?:enroll|add|register)\s+(?:me\s+)?(?:student\s+)?(?P<name>[a-z\s]+)\s+(?:in|dept|department)\s+(?P<dept>\w+)", re.I),
        'ANALYTICS_QUERY': re.compile(r"(?:campus|overall|department|show|calculate|what\s+are)\s+(?:me\s+)?(?:the\s+)?(?:campus\s+)?(?:analytics|stats|report|distribution|statistics|data)", re.I),
        'COUNT_QUERY': re.compile(r"how\s+many\s+students\s+(?:are\s+in|in|of)\s+(?P<dept>\w+)", re.I),
        'AT_RISK_LIST': re.compile(r"(?:who\s+is|list|show|which)\s+(?:me\s+)?(?:at\s+risk|critical|warning|risk)\s+students?", re.I),
    }

    DEPT_ALIASES = {
        'computer science': 'CS', 'computing': 'CS', 'it': 'IT', 'information technology': 'IT',
        'electronics': 'ECE', 'electrical': 'EEE', 'mechanical': 'MECH', 'mech': 'MECH',
        'civil': 'CIVIL', 'chemical': 'CHEM'
    }

    # --- Table Mappings ---
    TABLES = {
        'STUDENT_BY_ID': 'Students (students_student)',
        'ATTENDANCE_QUERY': 'Attendance (attendance_attendancerecord)',
        'LOW_ATTENDANCE': 'Attendance (attendance_attendancerecord)',
        'SCHOLARSHIP_ELIGIBLE': 'Scholarships (scholarships_scholarshipscheme)',
        'SCHOLARSHIP_LIST': 'Scholarships (scholarships_scholarshipscheme)',
        'FACULTY_DEPT': 'Faculty (faculty_faculty)',
        'FACULTY_LOAD': 'Faculty (faculty_faculty, faculty_facultyassignment)',
        'EXAM_SCHEDULE': 'Exams (exams_exam)',
        'TOP_STUDENTS': 'Exam Results (exams_examresult)',
        'ENROLL_STUDENT': 'Students (RAW UPDATE)',
        'ANALYTICS_QUERY': 'Students (Aggregation)',
        'COUNT_QUERY': 'Students (Count)',
        'AT_RISK_LIST': 'Attendance (Aggregation)',
    }

    @classmethod
    def get_roll_from_context(cls, user):
        """Extracts roll_no from the logged-in user object."""
        if not user: return None
        # Try standard attributes
        roll = getattr(user, 'username', None) or getattr(user, 'roll_no', None)
        if roll and re.match(r'[A-Z]+\d+', str(roll), re.I):
            return str(roll).upper()
        
        # Fallback: Query Student Table by Email
        if getattr(user, 'email', None):
            try:
                from students.models import Student
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("SELECT roll_no FROM students_student WHERE email = %s LIMIT 1", [user.email])
                    row = cursor.fetchone()
                    if row: return row[0]
            except: pass
        return None

    @classmethod
    def process(cls, message, user=None):
        message = message.lower().strip()
        
        # Priority 1: Welcome message for very short help queries
        if message in ['hi', 'hello', 'help', 'what can you do', 'hey']:
             return cls.get_welcome_message()

        intent = None
        params = {}

        # Step 1: Intent Understanding (Regex Matching)
        for name, pattern in cls.PATTERNS.items():
            match = pattern.search(message)
            if match:
                intent = name
                params = match.groupdict()
                break

        if not intent:
            return None

        print(f"[CampusAI] [STEP 1] Advanced Intent Analysis: '{message}'")
        # Step 3: Logic Execution (DB Actions)
        role = getattr(user, 'role', 'student') if user else 'student'
        return cls.execute(intent, params, role, user)

    @classmethod
    def execute(cls, intent, params, role, user_obj=None):
        print(f"[CampusAI] [STEP 2] Identified Domain: {intent}")
        
        from django.db import connection
        
        # Resolve 'me/my/mine' for students
        target_roll = params.get('id')
        if not target_roll and user_obj:
             target_roll = cls.get_roll_from_context(user_obj)

        with connection.cursor() as cursor:
            # 1. Student Lookup & Search
            if intent == 'STUDENT_BY_ID' or intent == 'STUDENT_SEARCH':
                roll = (target_roll or params.get('id') or params.get('query', '')).upper()
                # Check for roll no
                cursor.execute("SELECT name, department, year, email, phone, marks_12th FROM students_student WHERE roll_no = %s OR name LIKE %s", [roll, f"%{roll}%"])
                rows = cursor.fetchall()
                if not rows: return {"text": f"I couldn't find any student record for '{roll}' in our database.", "type": "error"}
                
                if len(rows) == 1:
                    r = rows[0]
                    return {"text": f"Found: {r[0]} ({roll}) | Dept: {r[1]} | Yr: {r[2]} | GPA: {r[5]} | Email: {r[3]}", "type": "text"}
                
                lines = [f"- {r[0]} ({r[1]}) - {r[3]}" for r in rows[:5]]
                return {"text": f"Found {len(rows)} matches:\n" + "\n".join(lines), "type": "text"}

            # 2. Record Update
            if intent == 'UPDATE_STUDENT':
                if role != 'admin' and role != 'teacher':
                    return {"text": "Access Denied: You do not have permission to update student records.", "type": "error"}
                
                roll = params.get('id', '').upper()
                field = params.get('field', '').lower()
                val = params.get('value', '').strip()
                
                # Field Mapping
                db_field = 'department' if field in ['dept', 'department'] else 'marks_12th' if field == 'gpa' else field
                
                try:
                    cursor.execute(f"UPDATE students_student SET {db_field} = %s WHERE roll_no = %s", [val, roll])
                    if cursor.rowcount == 0:
                        return {"text": f"Student {roll} not found for update.", "type": "error"}
                    return {"text": f"Student {roll} updated successfully. Field: {field} -> {val}", "type": "text"}
                except Exception as e:
                    return {"text": f"Failed to update record: {str(e)}", "type": "error"}

            # 3. Attendance Intelligence
            if intent == 'ATTENDANCE_QUERY':
                roll = (target_roll or '').upper()
                if not roll: return {"text": "Please provide a Roll No or log in to check your own attendance.", "type": "warning"}
                
                cursor.execute("""
                    SELECT 
                        COUNT(*), 
                        SUM(CASE WHEN status='present' THEN 1 ELSE 0 END)
                    FROM attendance_attendancerecord WHERE roll_no = %s
                """, [roll])
                res = cursor.fetchone()
                if not res or res[0] == 0: return {"text": f"No attendance data found for {roll}.", "type": "error"}
                
                total, present = res[0], res[1] or 0
                pct = (present/total)*100
                status = "Safe" if pct >= 75 else "At Risk"
                return {"text": f"Attendance for {roll}: {present}/{total} days ({pct:.1f}%). Status: {status}.", "type": "text"}

            # 4. Scholarship Eligibility Engine
            if intent == 'SCHOLARSHIP_ELIGIBLE':
                roll = (target_roll or '').upper()
                if not roll: return {"text": "I can help check scholarship eligibility! Please provide your Roll No or use 'Check my scholarship'.", "type": "warning"}
                
                cursor.execute("SELECT name, marks_12th, caste, department FROM students_student WHERE roll_no = %s", [roll])
                s = cursor.fetchone()
                if not s: return {"text": "Student profile not found.", "type": "error"}
                
                name, marks, caste, dept = s[0], s[1], s[2], s[3]
                cursor.execute("SELECT name, eligibility_criteria FROM scholarships_scholarshipscheme")
                schemes = cursor.fetchall()
                
                eligible = []
                for s_name, criteria in schemes:
                    if isinstance(criteria, str): criteria = json.loads(criteria)
                    
                    ok = True
                    if 'marks_min' in criteria and marks < criteria['marks_min']: ok = False
                    if 'caste' in criteria and caste != criteria['caste']: ok = False
                    
                    if ok: eligible.append(f"- {s_name}")
                
                if eligible:
                    return {"text": f"Good news {name}! You are eligible for:\n" + "\n".join(eligible), "type": "text"}
                return {"text": f"Sorry {name}, you don't seem to meet the specific criteria for current active schemes.", "type": "text"}

            # 5. Scholarship List
            elif intent == 'SCHOLARSHIP_LIST':
                cursor.execute("SELECT name, link FROM scholarships_scholarshipscheme")
                rows = cursor.fetchall()
                if not rows: return {"text": "No active scholarship schemes found.", "type": "text"}
                list_str = "\n".join([f"- **{r[0]}**: {r[1] or 'Check official portal'}" for r in rows])
                return {"text": f"Active Scholarship Schemes:\n{list_str}", "type": "text"}

            # 6. Top Students
            elif intent == 'TOP_STUDENTS':
                cursor.execute("""
                    SELECT s.name, r.marks, r.grade, s.department 
                    FROM exams_examresult r
                    JOIN students_student s ON r.roll_no = s.roll_no
                    ORDER BY r.marks DESC LIMIT 5
                """)
                rows = cursor.fetchall()
                if not rows: return {"text": "No exam results found to calculate toppers.", "type": "text"}
                lines = [f"{i+1}. {r[0]} ({r[3]}) - {r[1]}% [{r[2]}]" for i, r in enumerate(rows)]
                return {"text": "Top Performing Students:\n" + "\n".join(lines), "type": "text"}

            # 6. Faculty Workload
            elif intent == 'FACULTY_LOAD':
                fname = f"%{params.get('name', '')}%"
                cursor.execute("""
                    SELECT f.name, f.department, GROUP_CONCAT(c.name)
                    FROM faculty_faculty f
                    LEFT JOIN faculty_facultyassignment a ON f.id = a.faculty_id
                    LEFT JOIN courses_course c ON a.course_id = c.id
                    WHERE f.name LIKE %s
                    GROUP BY f.id
                """, [fname])
                row = cursor.fetchone()
                if not row or not row[0]: return {"text": f"Faculty '{params.get('name')}' not found.", "type": "error"}
                courses = row[2] if row[2] else "No courses assigned"
                return {"text": f"Faculty: {row[0]} ({row[1]})\nAssigned Courses: {courses}", "type": "text"}

            # 7. Low Attendance List (At-Risk Students)
            elif intent == 'LOW_ATTENDANCE' or intent == 'AT_RISK_LIST':
                limit_val = params.get('limit') or 75
                limit = int(limit_val)
                cursor.execute("""
                    SELECT s.name, s.roll_no, 
                           ROUND(100.0 * SUM(CASE WHEN status='present' THEN 1 ELSE 0 END) / COUNT(*), 1) as pct
                    FROM attendance_attendancerecord r
                    JOIN students_student s ON r.roll_no = s.roll_no
                    GROUP BY s.roll_no
                    HAVING pct < %s
                """, [limit])
                rows = cursor.fetchall()
                if not rows: return {"text": f"No students found with attendance below {limit}%.", "type": "text"}
                lines = [f"- {r[0]} ({r[1]}): {r[2]}%" for r in rows]
                return {"text": f"Students with low attendance (<{limit}%):\n" + "\n".join(lines), "type": "text"}

            # 8. Analytics & Counting (Advanced Logistics)
            if intent == 'ANALYTICS_QUERY':
                # Advanced Analytical Response
                cursor.execute("SELECT AVG(marks_12th) FROM students_student")
                avg_gpa = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT department, COUNT(*) FROM students_student GROUP BY department")
                dist = cursor.fetchall()
                
                res = f"### Campus Statistics Report\n"
                res += f"- **Average GPA (University):** {avg_gpa:.2f}\n"
                res += f"- **Total Students:** {sum(d[1] for d in dist)}\n\n"
                res += "**Student Distribution by Department:**\n"
                for d, count in dist: res += f"- {d}: {count} students\n"
                return {"text": res, "type": "text"}

            if intent == 'COUNT_QUERY':
                dept = params.get('dept', '').upper()
                cursor.execute("SELECT COUNT(*) FROM students_student WHERE department = %s", [dept])
                count = cursor.fetchone()[0]
                return {"text": f"There are **{count}** students currently enrolled in the **{dept}** department.", "type": "text"}

            # 9. Enrollment Logic (Administrative)
            if intent == 'ENROLL_STUDENT':
                if role != 'teacher' and role != 'admin':
                    return {"text": "Access Denied: Only staff can enroll new students via chat.", "type": "error"}
                
                name = params.get('name', '').title()
                dept = params.get('dept', '').upper()
                roll = f"{dept}{__import__('random').randint(1000, 9999)}"
                email = f"{roll.lower()}@student.edu"
                
                # We use cursor to be 24/7 safe (raw SQL)
                cursor.execute("INSERT INTO students_student (roll_no, name, department, year, email, phone, marks_12th) VALUES (%s, %s, %s, 1, %s, 'N/A', 0)", 
                               [roll, name, dept, email])
                return {"text": f"**Success!** Student **{name}** has been enrolled in **{dept}**.\n- Generated Roll No: `{roll}`\n- Generated Email: `{email}`", "type": "text"}

            # 4. Faculty Intelligence
            if intent == 'FACULTY_DEPT':
                dept = params.get('dept', '').upper()
                cursor.execute("SELECT name, email FROM faculty_faculty WHERE department = %s", [dept])
                rows = cursor.fetchall()
                if rows:
                    res = f"### Faculty Members in {dept}\n"
                    for r in rows: res += f"- **{r[0]}** ({r[1]})\n"
                    return {"text": res, "type": "text"}
                return {"text": f"No faculty listed for {dept} yet.", "type": "text"}

            # 5. Exam Scheduler
            if intent == 'EXAM_SCHEDULE':
                cursor.execute("SELECT c.name, e.date, e.room FROM exams_exam e JOIN courses_course c ON e.course_id = c.id WHERE e.date >= date('today') ORDER BY e.date")
                rows = cursor.fetchall()
                if rows:
                    res = "### Upcoming Exam Schedule\n"
                    for r in rows: res += f"- **{r[0]}** on {r[1]} | Room: {r[2]}\n"
                    return {"text": res, "type": "text"}
                return {"text": "No upcoming exams scheduled.", "type": "text"}

        return {"text": "Advanced intent recognized but DB execution is pending.", "type": "warning"}

    @classmethod
    def get_welcome_message(cls):
        return {
            "text": "Hello! I am **CampusAI**, your upgraded 24/7 offline assistant. \n\n"
                    "I am now **CONTEXT-AWARE**. You can ask:\n"
                    "- `Who is student CS1001?` (Lookup)\n"
                    "- `Am I eligible for any scholarships?` (Self-Check)\n"
                    "- `Show my attendance` (Personalized)\n"
                    "- `List faculty in CS` (Directory)\n\n"
                    "How can I help you today?",
            "type": "text"
        }

class LocalBrain:
    """Advanced Entry Point for AgentRouter."""
    @staticmethod
    def process(message, user=None):
        res = CampusAI.process(message, user)
        if res: return res
        return {
            "text": "I am CampusAI (Offline Mode). Cloud APIs are currently exhausted, but I can still assist with database actions. Please try the examples in 'help'.",
            "type": "error"
        }
