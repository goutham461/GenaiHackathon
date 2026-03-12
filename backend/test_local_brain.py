import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from agents.utils.router import AgentRouter
from django.conf import settings

def test_local_brain():
    print("--- Testing LocalBrain (Offline Mode) ---")
    
    # Force Gemini disabled to trigger LocalBrain
    setattr(settings, 'GEMINI_DISABLED', True)
    
    router = AgentRouter()
    router.role = 'teacher'
    
    test_queries = [
        "hi",
        "who is student CS3336",
        "how many students are eligible for laptop scheme",
        "list students with low attendance",
        "show attendance for CS8774"
    ]
    
    for q in test_queries:
        print(f"\nUser: {q}")
        response = router.route(q)
        print(f"CampusAI: {response}")

if __name__ == "__main__":
    test_local_brain()
