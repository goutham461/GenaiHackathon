import os
import django
import sys
from unittest.mock import MagicMock

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from users.models import User
from students.models import Student
from agents.utils.router import AgentRouter

def test_mocked():
    # Make sure we have a teacher
    teacher_user, _ = User.objects.get_or_create(email='teacher@college.edu', defaults={'role': 'teacher', 'username': 'teacher_test'})
    
    # Ensure student CS1418 exists for the test
    Student.objects.get_or_create(roll_no="CS1418", defaults={'name': 'Alice Johnson', 'email': 'alice@college.edu', 'department': 'CS'})

    print(f"Testing as user: {teacher_user.email} (Teacher)")
    router = AgentRouter(user=teacher_user)
    
    # Mock the Gemini client to return predetermined SQL and response
    mock_client = MagicMock()
    router.client = mock_client
    
    # Setup mock behavior for Stage 1 (SQL Generation) and Stage 3 (NLP formatting)
    mock_client.models.generate_content.side_effect = [
        # Test 1: Combined SQL + response template for CS1418 lookup
        MagicMock(text='{"sql": "SELECT name FROM students_student WHERE roll_no = \'CS1418\'", "response": "The student with ID CS1418 is: {{RESULTS}}"}'),
        
        # Test 2: Attendance for CS1002
        MagicMock(text='{"sql": "SELECT * FROM attendance_attendancerecord WHERE roll_no = \'CS1002\'", "response": "Here is the attendance for CS1002: {{RESULTS}}"}'),
        
        # Test 3: List students
        MagicMock(text='{"sql": "SELECT name FROM students_student LIMIT 5", "response": "Here are the students with low attendance: {{RESULTS}}"}'),
    ]

    print("\n--- Test 1: Single ID lookup ---")
    resp1 = router.route("give name of the student in thse id CS1418")
    print("Response:")
    print(resp1)

    print("\n--- Test 2: Table lookup ---")
    resp2 = router.route("show attendance for CS1002")
    print("Response:")
    print(resp2)
    
    print("\n--- Test 3: Relational Lookup ---")
    resp3 = router.route("list students with low attendance")
    print("Response:")
    print(resp3)

if __name__ == "__main__":
    test_mocked()
