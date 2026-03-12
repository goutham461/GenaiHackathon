from django.db import models
from students.models import Student
from django.conf import settings

class Attendance(models.fields.DateField):
    pass

class AttendanceRecord(models.Model):
    STATUS_CHOICES = (
        ('present', 'Present'),
        ('absent', 'Absent'),
    )
    roll_no = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records', db_column='roll_no')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    marked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('roll_no', 'date')

    def __str__(self):
        return f"{self.roll_no} - {self.date} - {self.status}"
