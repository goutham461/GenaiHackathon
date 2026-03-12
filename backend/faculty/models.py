from django.db import models
from courses.models import Course

class Faculty(models.Model):
    name = models.CharField(max_length=255)
    department = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(max_length=255, unique=True, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    workload_hours = models.IntegerField(default=0)

    def __str__(self):
        return self.name

class FacultyAssignment(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='assignments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    semester = models.IntegerField(blank=True, null=True)
    academic_year = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.faculty.name} - {self.course.name}"
