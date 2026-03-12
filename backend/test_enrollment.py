import os
import django
import sys
from unittest.mock import MagicMock

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from agents.utils.router import AgentRouter

def test_enroll():
    print("--- Testing Enrollment Query ---")
    mock_user = MagicMock()
    mock_user.role = 'admin'
    mock_user.email = 'admin@uni.edu'
    
    router = AgentRouter(user=mock_user)
    
    query = "Enroll student Rahul in IT"
    print(f"Query: {query}")
    try:
        res = router.route(query)
        print(f"Result: {res}")
    except Exception as e:
        import traceback
        print(f"CRASHED with error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_enroll()
