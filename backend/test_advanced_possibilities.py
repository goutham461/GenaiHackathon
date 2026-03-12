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

def test_advanced_possibilities():
    print("--- Testing Advanced CampusAI (Analytics & Admin) ---")
    setattr(settings, 'GEMINI_DISABLED', True)
    
    # Simulate Teacher
    teacher = User.objects.filter(role='teacher').first()
    if not teacher:
        print("Creating temp teacher...")
        teacher = User.objects.create(email='test_teacher@edu.com', username='teacher_test', role='teacher')

    router = AgentRouter(user=teacher)
    
    test_queries = [
        "hi",
        "how many students in CS",
        "show campus analytics",
        "enroll Karthik in IT",
        "how many students in IT"
    ]
    
    for q in test_queries:
        print(f"\nUser: {q}")
        response = router.route(q)
        print(f"CampusAI: {response}")

if __name__ == "__main__":
    test_advanced_possibilities()
