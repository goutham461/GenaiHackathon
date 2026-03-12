
import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from agents.utils.router import AgentRouter
from django.contrib.auth import get_user_model

def test_live():
    User = get_user_model()
    # Try with a teacher user
    user = User.objects.filter(role='teacher').first()
    if not user:
        user = User.objects.create(username='testteacher', email='teacher@test.com', role='teacher')
    
    router = AgentRouter(user=user)
    
    queries = [
        "hi",
        "give name of the student with id CS1001",
        "show attendance for CS1002",
    ]
    
    print(f"Testing with User: {user.email} ({user.role})")
    for q in queries:
        print(f"\nQuery: {q}")
        try:
            resp = router.route(q)
            print(f"Response: {resp}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_live()
