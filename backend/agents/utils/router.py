"""
Gemini-powered Agent Router (google.genai SDK)
8 domain-isolated agents with real DB actions.
"""
import re
import os
from datetime import date, timedelta
from django.conf import settings
from django.db.models import Avg, Count


# ── DB Models ──────────────────────────────────────────────────────────────────
from students.models import Student
from attendance.models import AttendanceRecord
from faculty.models import Faculty, FacultyAssignment
from exams.models import Exam, ExamResult
from courses.models import Course
from scholarships.models import ScholarshipScheme
from agents.models import Agent, AgentAction
from letters.models import Letter


# ── Gemini Client ─────────────────────────────────────────────────────────────
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
        'warning':    ['risk', 'warning', 'safe zone', 'days needed', 'check risk'],
        'student':    ['enroll', 'delete student', 'list students', 'find student', 'add student'],
        'attendance': ['attendance', 'mark present', 'mark absent', 'absent', 'present', 'low attendance'],
        'exam':       ['exam', 'midterm', 'final', 'schedule', 'result', 'marks', 'grade', 'top students'],
        'faculty':    ['faculty', 'professor', 'workload', 'assign subject', 'prof.'],
        'scholarship':['scholarship', 'eligible', 'scheme', 'grant', 'laptop', 'tn laptop', 'ambedkar', 'welfare'],
        'letter':     ['letter', 'permission', 'bonafide', 'noc', 'internship', 'hackathon letter'],
        'analytics':  ['stats', 'analytics', 'pass rate', 'trend', 'pass percentage', 'report'],
    }

    def __init__(self, user=None):
        self.user = user
        self.role = getattr(user, 'role', 'student')
        self.client = None
        if _genai_available and settings.GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────
    # MAIN ROUTER
    # ─────────────────────────────────────────────────────────────────
    def route(self, message: str) -> str:
        msg_lower = message.lower()

        # Role-gate first
        if self.role == 'student':
            if any(kw in msg_lower for kw in ['enroll', 'delete student', 'analytics', 'pass rate', 'all students']):
                return "⛔ **Access Denied**: This action is restricted to Teachers only."

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

        # Fall back to Gemini for general Q&A
        return self._gemini_general(message)

    def _detect_domain(self, msg_lower: str):
        for domain, keywords in self.AGENT_KEYWORDS.items():
            if any(kw in msg_lower for kw in keywords):
                return domain
        return None

    def extract_roll_no(self, text: str):
        match = re.search(r'\b[A-Za-z]{2}\d{4}\b', text.upper())
        return match.group(0) if match else None

    # ─────────────────────────────────────────────────────────────────
    # GEMINI GENERAL Q&A  (with quota fallback)
    # ─────────────────────────────────────────────────────────────────
    def _gemini_general(self, message: str) -> str:
        if not self.client:
            return self._fallback_help()

        total_students = Student.objects.count()
        high_risk = self._count_risk_students()
        context = (
            f"You are CampusAI, the smart assistant for a university management system.\n"
            f"Current user role: {self.role}.\n"
            f"Campus: {total_students} students enrolled, {high_risk} at attendance risk.\n"
            f"8 specialized agents: Warning, Student, Attendance, Exam, Faculty, Scholarship, Letter, Analytics.\n"
            f"Answer concisely. If real DB data is needed, guide the user to use the correct command."
        )
        import time
        last_err = None
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=f"{context}\n\nUser: {message}"
                )
                return response.text
            except Exception as e:
                last_err = str(e)
                # Quota / rate-limit error — fall back immediately, no point retrying
                if '429' in last_err or 'RESOURCE_EXHAUSTED' in last_err or 'quota' in last_err.lower():
                    return self._fallback_help(quota_hit=True)
                if attempt < 2:
                    time.sleep(2 ** attempt)  # 1s, 2s backoff
        return f"⚠️ Campus AI temporarily unavailable. Error: {last_err}"

    def _fallback_help(self, quota_hit: bool = False) -> str:
        note = (
            "\n\n> ⚠️ *Gemini quota exceeded for today. Using built-in agents — all DB features still work!*"
            if quota_hit else ""
        )
        return (
            "👋 **Campus AI — Command Guide:**\n\n"
            "**Attendance:**\n"
            "- `Check risk for CS1001` — Attendance risk + days needed\n"
            "- `Attendance for CS1002` — View log\n"
            "- `Low attendance list` — All students below 75%\n\n"
            "**Students:** (Teacher only)\n"
            "- `Enroll Ravi CS1010` — Add new student\n"
            "- `List students CS` — All CS students\n\n"
            "**Exams:**\n"
            "- `Upcoming exams` — Show schedule\n"
            "- `Top students` — Rank by marks\n\n"
            "**Scholarships:**\n"
            "- `Scholarship for CS1001` — Check eligibility\n\n"
            "**Letters:**\n"
            "- `Generate bonafide for CS1001` — Create letter\n\n"
            "**Analytics:** (Teacher only)\n"
            "- `Campus analytics` — Full stats"
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

    # ─────────────────────────────────────────────────────────────────
    # 1. WARNING AGENT
    # ─────────────────────────────────────────────────────────────────
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
                        at_risk.append(f"- **{s.name}** ({s.roll_no}): {pct:.1f}% [{risk}] — needs {needed} more days")
            if at_risk:
                return f"⚠️ **{len(at_risk)} Students At Risk:**\n" + "\n".join(at_risk)
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
            emoji = "🔴" if pct < 65 else "🟡" if pct < 75 else "🟢"
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
                out += "🔔 Auto-alert would be sent to HOD and student's parent."
            return out
        except Student.DoesNotExist:
            return f"Student {roll} not found in database."

    # ─────────────────────────────────────────────────────────────────
    # 2. STUDENT AGENT
    # ─────────────────────────────────────────────────────────────────
    def agent_student(self, message: str) -> str:
        if self.role != 'teacher':
            return "⛔ Access Denied: Only teachers can manage student records."

        msg_lower = message.lower()
        if 'list' in msg_lower or 'show' in msg_lower:
            dept_match = re.search(r'\b(CS|IT|ECE|EEE|MECH)\b', message.upper())
            dept = dept_match.group(0) if dept_match else None
            qs = Student.objects.filter(department=dept) if dept else Student.objects.all()
            total = qs.count()
            students = qs[:10]
            if not students: return "No students found."
            lines = [f"- **{s.name}** ({s.roll_no}) | {s.department} Yr{s.year} | {s.email}" for s in students]
            return f"👥 **Students {'in ' + dept if dept else '(All)'} — {total} total:**\n" + "\n".join(lines)

        # Use Gemini to extract entities dynamically
        extracted = {}
        if self.client:
            prompt = (
                "Extract student enrollment/deletion details from the user's message as JSON.\n"
                "Return ONLY a raw JSON object with no markdown wrappers or backticks.\n"
                "Keys: action (enroll, delete, unknown), name, roll_no, email, password, department.\n"
                "If roll_no is missing, generate a random one like 'CS1099'.\n"
                f"Message: '{message}'"
            )
            try:
                res = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                import json
                text = res.text.strip(' `\n').replace('json\n', '')
                extracted = json.loads(text)
            except Exception as e:
                # Fallback to robust regex parsing if Gemini Quota is dead
                if 'enroll' in msg_lower or 'add' in msg_lower:
                    extracted['action'] = 'enroll'
                    # Extract email
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+', msg_lower)
                    if email_match: extracted['email'] = email_match.group(0)
                    
                    # Extract name (words between "name" and "email", or "student" and "email")
                    name_match = re.search(r'(?:name|student)\s+([a-z\s]+?)\s+(?:email|pass)', msg_lower)
                    if name_match: 
                        raw_name = name_match.group(1).replace('or enroll', '').replace('enroll', '').strip()
                        extracted['name'] = raw_name.title()
                    
                    # Extract password
                    pass_match = re.search(r'(?:pass|password)\s+(\S+)', message, re.IGNORECASE)
                    if pass_match: extracted['password'] = pass_match.group(1).strip()
                    
                    # Extract roll no (e.g. CS1090)
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
                defaults={'name': name, 'department': dept, 'year': 1, 'email': email}
            )
            
            if created_student or created_user:
                return (f"✅ **Student Successfully Enrolled!**\n\n"
                        f"- **Name:** {student.name}\n"
                        f"- **Roll No:** {student.roll_no}\n"
                        f"- **Email:** {email}\n"
                        f"- **Password:** `{password}`\n\n"
                        f"They can now log in to the student portal.")
            else:
                return f"ℹ️ Student {roll.upper()} or {email} already exists."

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
                    return f"🗑️ **Deleted:** {name} ({roll.upper()}) and their auth account."
                except Student.DoesNotExist:
                    return f"Student {roll.upper()} not found."
            return "Format: *Delete [RollNo]*"

        return "Student Agent commands: 'add student [Name] email [Email] passed [Pass]' or 'Delete [RollNo]'"

    # ─────────────────────────────────────────────────────────────────
    # 3. ATTENDANCE AGENT
    # ─────────────────────────────────────────────────────────────────
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
                return f"✅ **{student.name}** marked **{status_val.upper()}** today.\nCurrent attendance: {pct:.1f}% ({present}/{total})"
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
                    f"📋 **Attendance: {student.name} ({roll})**\n"
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
            return f"⚠️ **Students Below {threshold}%:**\n" + "\n".join(low)
        return "All students are above the attendance threshold."

    # ─────────────────────────────────────────────────────────────────
    # 4. EXAM AGENT
    # ─────────────────────────────────────────────────────────────────
    def agent_exam(self, message: str) -> str:
        msg = message.lower()

        # Top students
        if 'top' in msg or 'rank' in msg or 'best' in msg:
            results = ExamResult.objects.select_related('roll_no', 'exam').order_by('-marks')[:10]
            if results:
                lines = [f"{i+1}. **{r.roll_no.name}** ({r.roll_no.roll_no}) — {r.marks}% [{r.grade}] | {r.exam.course.name}" for i, r in enumerate(results)]
                return "🏆 **Top Students (Exam Results):**\n" + "\n".join(lines)
            return "No exam results found."

        # Upcoming exams
        upcoming = Exam.objects.filter(date__gte=date.today()).order_by('date').select_related('course', 'invigilator')
        if upcoming.exists():
            lines = [f"- **{e.course.name}** ({e.exam_type.title()}) — {e.date} | Room: {e.room} | Invigilator: {e.invigilator.name}" for e in upcoming]
            return "📚 **Upcoming Exams:**\n" + "\n".join(lines)
        return "No upcoming exams scheduled."

    # ─────────────────────────────────────────────────────────────────
    # 5. FACULTY AGENT
    # ─────────────────────────────────────────────────────────────────
    def agent_faculty(self, message: str) -> str:
        faculties = Faculty.objects.all()
        lines = []
        for f in faculties:
            assignments = FacultyAssignment.objects.filter(faculty=f).select_related('course')
            courses = ", ".join([a.course.name for a in assignments]) or "No courses assigned"
            load = assignments.count() * 3  # mock 3 hrs/course
            lines.append(f"- **{f.name}** ({f.department}) | {courses} | Workload: ~{load}hrs/week")
        return "👨🏫 **Faculty Directory:**\n" + "\n".join(lines) if lines else "No faculty records found."

    # ─────────────────────────────────────────────────────────────────
    # 6. SCHOLARSHIP AGENT
    # ─────────────────────────────────────────────────────────────────
    def agent_scholarship(self, message: str) -> str:
        roll = self.extract_roll_no(message)
        msg_lower = message.lower()
        schemes = ScholarshipScheme.objects.all()

        # Did user ask who is eligible for a specific scheme?
        if not roll and ('who' in msg_lower or 'list' in msg_lower or 'eligible' in msg_lower):
            # Try to match scheme name words (e.g. "laptop", "ambedkar")
            target_scheme = next((s for s in schemes if any(w in msg_lower for w in s.name.lower().split() if len(w) > 3)), None)
            
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
                    return f"✅ **Students currently eligible for {target_scheme.name}:**\n" + "\n".join(eligible_students)
                return f"No students currently eligible for {target_scheme.name}."

        if not roll:
            lines = []
            for s in schemes:
                c = s.eligibility_criteria
                criteria_str = " | ".join([f"{k}: {v}" for k, v in c.items()])
                lines.append(f"- **{s.name}**: {criteria_str}")
            return "💰 **Active Scholarship Schemes:**\n" + "\n".join(lines)

        try:
            student = Student.objects.get(roll_no=roll)
            eligible, ineligible = [], []
            for s in schemes:
                c = s.eligibility_criteria
                reasons = []
                ok = True
                if 'income_max' in c and (student.annual_income or 0) > c['income_max']:
                    ok = False
                    reasons.append(f"income ₹{student.annual_income:,.0f} > max ₹{c['income_max']:,}")
                if 'marks_min' in c and (student.marks_12th or 0) < c['marks_min']:
                    ok = False
                    reasons.append(f"marks {student.marks_12th} < min {c['marks_min']}")
                if 'caste' in c and student.caste != c['caste']:
                    ok = False
                    reasons.append(f"caste {student.caste} ≠ required {c['caste']}")
                if ok:
                    eligible.append(f"✅ **{s.name}** — [Apply]({s.link})")
                else:
                    ineligible.append(f"❌ **{s.name}** — {', '.join(reasons)}")

            out = f"🎓 **Scholarship Report for {student.name} ({roll})**\n"
            out += f"*Caste: {student.caste} | Income: ₹{student.annual_income:,.0f} | 12th: {student.marks_12th}%*\n\n"
            if eligible:
                out += "**Eligible:**\n" + "\n".join(eligible) + "\n\n"
            if ineligible:
                out += "**Ineligible:**\n" + "\n".join(ineligible)
            return out
        except Student.DoesNotExist:
            return f"Student {roll} not found."

    # ─────────────────────────────────────────────────────────────────
    # 7. LETTER AGENT
    # ─────────────────────────────────────────────────────────────────
    def agent_letter(self, message: str) -> str:
        roll = self.extract_roll_no(message)
        msg = message.lower()

        if not roll:
            # Show pending letters
            pending = Letter.objects.filter(status='pending').count()
            hod_approved = Letter.objects.filter(status='hod_approved').count()
            final = Letter.objects.filter(status='final_approved').count()
            return (
                f"📜 **Letter Status Dashboard:**\n"
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
                f"📄 **Letter Request Created** (ID: #{letter.id})\n"
                f"- Student: {student.name} ({roll})\n"
                f"- Type: {letter_type.upper()}\n"
                f"- Status: ⏳ **Pending HOD Approval**\n\n"
                f"HOD can approve this in the *Letters Portal → HOD Dashboard*."
            )
        except Student.DoesNotExist:
            return f"Student {roll} not found."

    # ─────────────────────────────────────────────────────────────────
    # 8. ANALYTICS AGENT
    # ─────────────────────────────────────────────────────────────────
    def agent_analytics(self, message: str) -> str:
        if self.role == 'student':
            return "⛔ Analytics is restricted to Teachers only."

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
