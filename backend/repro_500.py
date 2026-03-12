import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from agents.utils.router import AgentRouter
from students.models import Student

class MockUser:
    def __init__(self):
        self.username = "admin"
        self.role = "teacher"
    def title(self):
        return "Teacher"

def test_router():
    user = MockUser()
    router = AgentRouter(user=user)
    
    # Clean up previous tests to avoid "already exists" info messages
    Student.objects.filter(name__icontains='bala').delete()
    
    queries = [
        'enroll one new student name bala , age 18 , department IT , caste bc'
    ]
    
    for q in queries:
        print(f"\nTesting AgentRouter.route('{q}')...")
        try:
            response = router.route(q)
            print(f"Response: {response}")
            
            # Verify in DB
            s = Student.objects.filter(name='Bala').first()
            if s:
                print(f">>> VERIFIED DB: Name={s.name}, Dept={s.department}, Caste={s.caste}")
                if s.name == 'Bala' and s.department == 'IT' and s.caste == 'bc':
                    print(">>> ALL FIELDS CORRECTLY PERSISTED!")
                else:
                    print(">>> SOME FIELDS MISMATCHED.")
            else:
                print(">>> FAILED: Student 'Bala' not found in database.")
                
        except Exception as e:
            print(f"FAILED '{q}' with error: {e}")

if __name__ == "__main__":
    test_router()
