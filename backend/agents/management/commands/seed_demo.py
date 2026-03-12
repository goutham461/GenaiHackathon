"""
Django management command to seed demo data.
Run: python manage.py seed_demo
"""
from django.core.management.base import BaseCommand
from users.models import User
from students.models import Student
from faculty.models import Faculty, FacultyAssignment
from courses.models import Course
from attendance.models import AttendanceRecord
from exams.models import Exam, ExamResult
from scholarships.models import ScholarshipScheme
from letters.models import Letter
from agents.models import Agent
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'Seed the database with rich demo data'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding database with rich demo data...")

        # --- USERS ---
        teacher, _ = User.objects.get_or_create(
            email="teacher@college.edu",
            defaults={"username": "teacher_user", "role": "teacher", "full_name": "Dr. Faculty Admin", "is_staff": True, "is_superuser": True},
        )
        teacher.set_password("admin123")
        teacher.is_staff = True
        teacher.is_superuser = True
        teacher.save()

        student_user, _ = User.objects.get_or_create(
            email="student@student.edu",
            defaults={"username": "student_user", "role": "student", "full_name": "Ravi Kumar"},
        )
        student_user.set_password("student123")
        student_user.save()
        self.stdout.write("  + Users created")

        # --- COURSES ---
        ds, _   = Course.objects.get_or_create(code="CS301", defaults={"name": "Data Structures", "department": "CS", "year": 3, "credits": 4})
        ai, _   = Course.objects.get_or_create(code="CS402", defaults={"name": "Artificial Intelligence", "department": "CS", "year": 4, "credits": 4})
        math, _ = Course.objects.get_or_create(code="MA201", defaults={"name": "Engineering Mathematics", "department": "CS", "year": 2, "credits": 3})
        os_, _  = Course.objects.get_or_create(code="CS302", defaults={"name": "Operating Systems", "department": "CS", "year": 3, "credits": 4})
        cn, _   = Course.objects.get_or_create(code="IT401", defaults={"name": "Computer Networks", "department": "IT", "year": 4, "credits": 3})
        self.stdout.write("  + Courses created")

        # --- FACULTY ---
        kumar, _  = Faculty.objects.get_or_create(email="kumar@college.edu",  defaults={"name": "Prof. Kumar", "department": "CS", "phone": "9876543210"})
        priya_f, _ = Faculty.objects.get_or_create(email="priya_f@college.edu", defaults={"name": "Dr. Priya Sharma", "department": "CS", "phone": "9876543211"})
        rajan, _  = Faculty.objects.get_or_create(email="rajan@college.edu",   defaults={"name": "Prof. Rajan Iyer", "department": "IT", "phone": "9876543212"})

        FacultyAssignment.objects.get_or_create(faculty=kumar, course=ds,   defaults={"semester": 3, "academic_year": "2025-26"})
        FacultyAssignment.objects.get_or_create(faculty=kumar, course=os_,  defaults={"semester": 3, "academic_year": "2025-26"})
        FacultyAssignment.objects.get_or_create(faculty=priya_f, course=ai, defaults={"semester": 4, "academic_year": "2025-26"})
        FacultyAssignment.objects.get_or_create(faculty=priya_f, course=math, defaults={"semester": 2, "academic_year": "2025-26"})
        FacultyAssignment.objects.get_or_create(faculty=rajan, course=cn,   defaults={"semester": 4, "academic_year": "2025-26"})
        self.stdout.write("  + Faculty & Assignments created")

        # --- STUDENTS (10 students with rich data) ---
        sample_students = [
            {"roll_no": "CS1001", "name": "Ravi Kumar",    "department": "CS", "year": 3, "email": "student@student.edu", "phone": "9000000001", "caste": "OC", "annual_income": 320000, "marks_12th": 88},
            {"roll_no": "CS1002", "name": "Priya Singh",   "department": "CS", "year": 3, "email": "priya@student.edu",   "phone": "9000000002", "caste": "SC", "annual_income": 150000, "marks_12th": 91},
            {"roll_no": "CS1003", "name": "Arun Raj",      "department": "CS", "year": 3, "email": "arun@student.edu",    "phone": "9000000003", "caste": "BC", "annual_income": 180000, "marks_12th": 85},
            {"roll_no": "CS1004", "name": "Meena Kumari",  "department": "CS", "year": 2, "email": "meena@student.edu",   "phone": "9000000004", "caste": "SC", "annual_income": 120000, "marks_12th": 93},
            {"roll_no": "CS1005", "name": "Siva Prasad",   "department": "CS", "year": 4, "email": "siva@student.edu",    "phone": "9000000005", "caste": "OC", "annual_income": 450000, "marks_12th": 76},
            {"roll_no": "IT2001", "name": "Anjali Nair",   "department": "IT", "year": 2, "email": "anjali@student.edu",  "phone": "9000000006", "caste": "BC", "annual_income": 200000, "marks_12th": 87},
            {"roll_no": "IT2002", "name": "Karthick Raja", "department": "IT", "year": 3, "email": "karthick@student.edu","phone": "9000000007", "caste": "MBC","annual_income": 160000, "marks_12th": 82},
            {"roll_no": "IT2003", "name": "Divya Mohan",   "department": "IT", "year": 4, "email": "divya@student.edu",   "phone": "9000000008", "caste": "OC", "annual_income": 380000, "marks_12th": 94},
            {"roll_no": "EC3001", "name": "Surya Durai",   "department": "ECE","year": 3, "email": "surya@student.edu",   "phone": "9000000009", "caste": "BC", "annual_income": 210000, "marks_12th": 79},
            {"roll_no": "EC3002", "name": "Nithya Lakshmi","department": "ECE","year": 2, "email": "nithya@student.edu",  "phone": "9000000010", "caste": "SC", "annual_income": 110000, "marks_12th": 95},
        ]
        for s in sample_students:
            roll = s.pop("roll_no")
            Student.objects.get_or_create(roll_no=roll, defaults=s)
        self.stdout.write("  + 10 Students created")

        # --- ATTENDANCE (30-day records) ---
        today = date.today()
        # Ravi: 58% (17/30 present) - HIGH RISK
        ravi = Student.objects.get(roll_no="CS1001")
        for i in range(30):
            day = today - timedelta(days=i)
            AttendanceRecord.objects.get_or_create(roll_no=ravi, date=day, defaults={"status": "present" if i < 17 else "absent"})

        # Meena: 60% - HIGH RISK
        meena = Student.objects.get(roll_no="CS1004")
        for i in range(30):
            day = today - timedelta(days=i)
            AttendanceRecord.objects.get_or_create(roll_no=meena, date=day, defaults={"status": "present" if i < 18 else "absent"})

        # Others: 80-95% - Safe
        safe_students = ["CS1002","CS1003","CS1005","IT2001","IT2002","IT2003","EC3001","EC3002"]
        for roll in safe_students:
            s = Student.objects.get(roll_no=roll)
            present_days = random.randint(23, 29)
            for i in range(30):
                day = today - timedelta(days=i)
                AttendanceRecord.objects.get_or_create(roll_no=s, date=day, defaults={"status": "present" if i < present_days else "absent"})
        self.stdout.write("  + Attendance records seeded (Ravi=57%, Meena=60%, others=80-95%)")

        # --- EXAMS ---
        exam1, _ = Exam.objects.get_or_create(
            course=ds, exam_type="midterm", date=today + timedelta(days=10),
            defaults={"room": "Room A101", "invigilator": kumar}
        )
        exam2, _ = Exam.objects.get_or_create(
            course=ai, exam_type="midterm", date=today + timedelta(days=14),
            defaults={"room": "Room B204", "invigilator": priya_f}
        )
        exam3, _ = Exam.objects.get_or_create(
            course=math, exam_type="final", date=today + timedelta(days=21),
            defaults={"room": "Auditorium", "invigilator": priya_f}
        )

        # Exam Results
        results = [
            ("CS1001", exam1, 72.0, "B"), ("CS1002", exam1, 88.0, "A"),
            ("CS1003", exam1, 65.0, "C"), ("CS1004", exam1, 91.0, "A+"),
            ("CS1005", exam1, 55.0, "D"), ("CS1002", exam2, 82.0, "A"),
            ("CS1004", exam2, 95.0, "A+"),
        ]
        for roll, exam, marks, grade in results:
            try:
                s = Student.objects.get(roll_no=roll)
                ExamResult.objects.get_or_create(exam=exam, roll_no=s, defaults={"marks": marks, "grade": grade})
            except Exception:
                pass
        self.stdout.write("  + Exams and results seeded")

        # --- SCHOLARSHIPS ---
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
        ScholarshipScheme.objects.get_or_create(name="MBC Student Grant", defaults={
            "eligibility_criteria": {"caste": "MBC", "income_max": 250000, "marks_min": 75},
            "link": "https://tn.gov.in/mbc"
        })
        self.stdout.write("  + 4 Scholarship schemes seeded")

        # --- DEMO LETTERS ---
        ravi_obj = Student.objects.get(roll_no="CS1001")
        priya_obj = Student.objects.get(roll_no="CS1002")
        Letter.objects.get_or_create(
            student_roll=ravi_obj, letter_type="hackathon",
            defaults={
                "purpose": "Hackathon Permission",
                "details": "Smart India Hackathon 2026, March 20-22, NIT Chennai",
                "content": f"Bonafide requesting permission for Ravi Kumar to attend SIH 2026",
                "status": "pending",
                "requested_by": teacher,
            }
        )
        Letter.objects.get_or_create(
            student_roll=priya_obj, letter_type="internship",
            defaults={
                "purpose": "Internship at TCS",
                "details": "Summer internship at TCS, Chennai, June-July 2026",
                "content": f"Bonafide requesting internship permission for Priya Singh at TCS",
                "status": "pending",
                "requested_by": teacher,
            }
        )
        self.stdout.write("  + Demo letters seeded (status: pending)")

        # --- AGENTS ---
        demo_agents = [
            {"name": "Attendance Warning Agent", "domain": "attendance", "system_prompt": "Tracks attendance, calculates days needed for 75% safe zone, alerts mentor and student.", "tools": ["calculate_risk", "send_mentor_email", "send_student_whatsapp"], "description": "Predicts student failure risk from attendance data"},
            {"name": "Student Management Agent", "domain": "student", "system_prompt": "Manages student records: enroll, delete, update, list with filters.", "tools": ["enroll_student", "delete_student", "list_students"], "description": "CRUD operations for student records"},
            {"name": "Exam Scheduler Agent", "domain": "exam", "system_prompt": "Schedules exams, allocates rooms, tracks top students per subject.", "tools": ["schedule_exam", "room_allocation", "top_students"], "description": "Manages exam scheduling and results"},
            {"name": "Scholarship Agent", "domain": "scholarship", "system_prompt": "Checks scholarship scheme eligibility based on student data.", "tools": ["check_scheme", "list_eligible_schemes"], "description": "Matches students to eligible scholarships"},
            {"name": "Letter Generation Agent", "domain": "letter", "system_prompt": "Generates permission letters and manages approval chain.", "tools": ["generate_letter", "send_approval_chain", "track_status"], "description": "Creates official letters and approval workflows"},
            {"name": "Analytics Agent", "domain": "analytics", "system_prompt": "Generates pass/fail stats, trends, and visual reports (read-only).", "tools": ["pass_fail_stats", "department_trends", "generate_report"], "description": "Read-only analytics and reporting"},
            {"name": "Faculty Workload Agent", "domain": "faculty", "system_prompt": "Assigns subjects to faculty, checks workload limits, generates reports.", "tools": ["assign_subject", "workload_report"], "description": "Faculty management and workload tracking"},
            {"name": "Course Management Agent", "domain": "course", "system_prompt": "Creates and manages course catalog, credits, and department assignments.", "tools": ["create_course", "list_courses", "modify_course"], "description": "Course catalog management"},
        ]
        for a in demo_agents:
            Agent.objects.get_or_create(name=a["name"], defaults={**a, "created_by": teacher})
        self.stdout.write("  + 8 demo agents created")

        self.stdout.write("\nDone! Credentials:")
        self.stdout.write("  Teacher : teacher@college.edu / admin123")
        self.stdout.write("  Student : student@student.edu / student123")
