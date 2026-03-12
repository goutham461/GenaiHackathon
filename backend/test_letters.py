import os
import django
import sys
from datetime import date

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from agents.utils.router import AgentRouter
from django.contrib.auth import get_user_model
from students.models import Student

User = get_user_model()

def test_letter_generation():
    print("--- Testing Formal Letter Generation ---")
    
    # Simulate a logged-in student (CS1001 - Ravi Kumar)
    try:
        user = User.objects.get(username='student_user')
    except User.DoesNotExist:
        # Create if doesnt exist (for local test)
        user = User.objects.filter(role='student').first()
        if not user:
             print("No student user found. Please run import_csv.py")
             return

    router = AgentRouter(user=user)
    
    test_queries = [
        "generate a letter for sick leave",
        "i need an onduty letter for hackathon",
        "generate bonafide for CS1001",
        "request for noc"
    ]
    
    for q in test_queries:
        print(f"\nUser Request: {q}")
        response = router.route(q)
        print(f"Agent Response:\n{response}")

if __name__ == "__main__":
    test_letter_generation()
