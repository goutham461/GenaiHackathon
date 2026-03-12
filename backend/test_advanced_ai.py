import os
import django
import sys
import time

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from agents.utils.router import AgentRouter
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

def test_advanced_campus_ai():
    print("--- Testing Advanced CampusAI (Context-Aware Mode) ---")
    
    # 1. Force Offline Mode
    setattr(settings, 'GEMINI_DISABLED', True)
    
    # 2. Simulate a logged-in student (Priya Singh CS1002)
    try:
        mock_user = User.objects.get(email='cs1002@student.edu')
    except User.DoesNotExist:
        # Fallback to any student if import was different
        mock_user = User.objects.filter(role='student').first()
        if not mock_user:
             print("No students found in DB. Run import_csv first.")
             return

    print(f"Logged in as: {mock_user.full_name} ({mock_user.username})")
    
    router = AgentRouter(user=mock_user)
    
    test_queries = [
        "hi",
        "who is student CS1001",
        "am i eligible for any scholarship",
        "show my attendance",
        "list faculty in CS",
        "upcoming exams"
    ]
    
    for q in test_queries:
        start = time.time()
        print(f"\nUser: {q}")
        response = router.route(q)
        end = time.time()
        print(f"CampusAI: {response}")
        print(f"[Profiling] Time: {(end-start)*1000:.2f}ms")

if __name__ == "__main__":
    test_advanced_campus_ai()
