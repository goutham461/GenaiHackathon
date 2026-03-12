import os
import django
import csv
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from students.models import Student

User = get_user_model()

CSV_PATH = r'c:\Users\Gowtham\Desktop\Hackathon\students.csv'

def import_students():
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found.")
        return

    with open(CSV_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            try:
                roll_no = row['StudentID']
                name = row['Name']
                email = row['Email']
                dept = row['Department']
                gpa = float(row['GPA'])
                # Mapping GPA to marks_12th (e.g., 4.0 scale to 100)
                marks = (gpa / 4.0) * 100
                grad_year = int(row['GraduationYear'])
                
                # Logic for academic year (simplified: GradYear 2024=4, 2025=3, etc.)
                current_academic_year = 2024
                year_of_study = grad_year - current_academic_year
                year_of_study = max(1, min(4, 5 - year_of_study))

                # 1. Create User
                user_obj, created_user = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'username': email,
                        'full_name': name,
                        'role': 'student'
                    }
                )
                if created_user:
                    user_obj.set_password('student123')
                    user_obj.save()

                # 2. Create Student Profile
                student_obj, created_student = Student.objects.update_or_create(
                    roll_no=roll_no,
                    defaults={
                        'name': name,
                        'email': email,
                        'department': dept[:50],
                        'year': year_of_study,
                        'marks_12th': marks
                    }
                )
                
                status = "Imported" if created_student else "Updated"
                # print(f"[{status}] {name} ({roll_no})")
                count += 1
            except Exception as e:
                print(f"Error processing row {row}: {e}")

    print(f"Successfully processed {count} students.")

if __name__ == "__main__":
    import_students()
