from django.db import models
from courses.models import Course
from faculty.models import Faculty
from students.models import Student

class Exam(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='exams')
    exam_type = models.CharField(max_length=50) # 'midterm', 'final'
    date = models.DateField()
    room = models.CharField(max_length=50, blank=True, null=True)
    invigilator = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.course.name} - {self.exam_type} - {self.date}"

class ExamResult(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    roll_no = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_results', db_column='roll_no')
    marks = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    grade = models.CharField(max_length=2, blank=True, null=True)

    def __str__(self):
        return f"{self.roll_no} - {self.exam} - {self.marks}"
