"""
Run with: ..\venv\Scripts\python.exe manage.py shell < seed.py
Seed script for demo data.
"""
from users.models import User
from students.models import Student
from faculty.models import Faculty, FacultyAssignment
from courses.models import Course
from attendance.models import AttendanceRecord
from exams.models import Exam, ExamResult
from scholarships.models import ScholarshipScheme
from agents.models import Agent
from datetime import date, timedelta

print("Seeding database with demo data...")

# ── Users ──────────────────────────────────────────────────────────────────
admin, _ = User.objects.get_or_create(
    email="admin@college.edu",
    defaults={"username": "admin_user", "role": "admin", "full_name": "Admin User"},
)
admin.set_password("admin123")
admin.is_staff = True
admin.is_superuser = True
admin.save()

mentor, _ = User.objects.get_or_create(
    email="mentor@college.edu",
    defaults={"username": "mentor_user", "role": "mentor", "full_name": "Dr. Mentor"},
)
mentor.set_password("mentor123")
mentor.save()

print("  ✓ Users created (admin / mentor)")

# ── Courses ────────────────────────────────────────────────────────────────
ds, _ = Course.objects.get_or_create(code="CS301", defaults={"name": "Data Structures", "department": "CS", "year": 3, "credits": 4})
math, _ = Course.objects.get_or_create(code="MA201", defaults={"name": "Engineering Mathematics", "department": "CS", "year": 2, "credits": 3})
ai, _ = Course.objects.get_or_create(code="CS402", defaults={"name": "Artificial Intelligence", "department": "CS", "year": 4, "credits": 4})
print("  ✓ Courses created")

# ── Faculty ────────────────────────────────────────────────────────────────
kumar, _ = Faculty.objects.get_or_create(email="kumar@college.edu", defaults={"name": "Prof. Kumar", "department": "CS", "phone": "9876543210"})
priya, _ = Faculty.objects.get_or_create(email="priya@college.edu", defaults={"name": "Dr. Priya", "department": "CS", "phone": "9876543211"})
FacultyAssignment.objects.get_or_create(faculty=kumar, course=ds, defaults={"semester": 3, "academic_year": "2025-26"})
FacultyAssignment.objects.get_or_create(faculty=priya, course=ai, defaults={"semester": 4, "academic_year": "2025-26"})
print("  ✓ Faculty & assignments created")

# ── Students ───────────────────────────────────────────────────────────────
sample_students = [
    {"roll_no": "CS1001", "name": "Ravi Kumar", "department": "CS", "year": 3, "phone": "+91-9000000001", "email": "ravi@student.edu", "caste": "OC", "annual_income": 320000, "marks_12th": 88},
    {"roll_no": "CS1002", "name": "Priya Singh", "department": "CS", "year": 3, "phone": "+91-9000000002", "email": "priya@student.edu", "caste": "SC", "annual_income": 150000, "marks_12th": 91},
    {"roll_no": "CS1003", "name": "Arun Raj", "department": "CS", "year": 3, "phone": "+91-9000000003", "email": "arun@student.edu", "caste": "BC", "annual_income": 180000, "marks_12th": 85},
]
for s in sample_students:
    Student.objects.get_or_create(roll_no=s["roll_no"], defaults={k: v for k, v in s.items() if k != "roll_no"})
print("  ✓ Students created")

# ── Attendance ─────────────────────────────────────────────────────────────
ravi = Student.objects.get(roll_no="CS1001")
today = date.today()
for i in range(30):
    day = today - timedelta(days=i)
    # Ravi only attends 17 out of 30 days (58%)
    status = "present" if i < 17 else "absent"
    AttendanceRecord.objects.get_or_create(roll_no=ravi, date=day, defaults={"status": status})

for s_roll in ["CS1002", "CS1003"]:
    s = Student.objects.get(roll_no=s_roll)
    for i in range(30):
        day = today - timedelta(days=i)
        status = "present" if i < 25 else "absent"  # 83%
        AttendanceRecord.objects.get_or_create(roll_no=s, date=day, defaults={"status": status})
print("  ✓ Attendance seeded (Ravi=58%, others=83%)")

# ── Exams ──────────────────────────────────────────────────────────────────
exam, _ = Exam.objects.get_or_create(
    course=ds, exam_type="midterm", date=today + timedelta(days=10),
    defaults={"room": "Room A", "invigilator": kumar}
)
print("  ✓ Exam scheduled")

# ── Scholarship Schemes ────────────────────────────────────────────────────
ScholarshipScheme.objects.get_or_create(name="TN Laptop 2026", defaults={
    "eligibility_criteria": {"income_max": 200000, "marks_min": 90},
    "link": "https://tn.gov.in/laptop"
})
ScholarshipScheme.objects.get_or_create(name="Ambedkar SC Scholarship", defaults={
    "eligibility_criteria": {"caste": "SC", "marks_min": 85, "income_max": 250000},
    "link": "https://tn.gov.in/ambedkar"
})
ScholarshipScheme.objects.get_or_create(name="BC Welfare Scholarship", defaults={
    "eligibility_criteria": {"caste": "BC", "income_max": 200000},
    "link": "https://tn.gov.in/bcwelfare"
})
print("  ✓ Scholarship schemes seeded")

# ── Pre-built Agents ───────────────────────────────────────────────────────
demo_agents = [
    {"name": "Attendance Warning Agent", "domain": "attendance", "system_prompt": "Tracks attendance, calculates days needed for 75% safe zone, alerts mentor and student.", "tools": ["calculate_risk", "send_mentor_email", "send_student_whatsapp"], "description": "Predicts student failure risk from attendance data"},
    {"name": "Student Management Agent", "domain": "student", "system_prompt": "Manages student records: enroll, delete, update, list with filters.", "tools": ["enroll_student", "delete_student", "list_students", "update_student"], "description": "CRUD operations for student records"},
    {"name": "Exam Scheduler Agent", "domain": "exam", "system_prompt": "Schedules exams, allocates rooms, tracks top students per subject.", "tools": ["schedule_exam", "room_allocation", "top_students"], "description": "Manages exam scheduling and results"},
    {"name": "Scholarship Agent", "domain": "scholarship", "system_prompt": "Checks scholarship scheme eligibility based on student data.", "tools": ["check_scheme", "list_eligible_schemes"], "description": "Matches students to eligible scholarships"},
    {"name": "Letter Generation Agent", "domain": "letter", "system_prompt": "Generates permission letters and manages approval chain.", "tools": ["generate_letter", "send_approval_chain", "track_status"], "description": "Creates official letters and approval workflows"},
    {"name": "Analytics Agent", "domain": "analytics", "system_prompt": "Generates pass/fail stats, trends, and visual reports.", "tools": ["pass_fail_stats", "department_trends", "generate_report"], "description": "Read-only analytics and reporting"},
]
for a in demo_agents:
    Agent.objects.get_or_create(name=a["name"], defaults={**a, "created_by": admin})
print("  ✓ 6 demo agents created")

print("\n✅ All done! Demo credentials:")
print("   Mentor  → mentor@college.edu  / mentor123")
print("   Admin   → admin@college.edu   / admin123")
