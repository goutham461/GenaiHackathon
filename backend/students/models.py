from django.db import models

class Student(models.Model):
    roll_no = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=255)
    department = models.CharField(max_length=50, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    caste = models.CharField(max_length=50, blank=True, null=True)
    annual_income = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    marks_12th = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    gpa = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    join_year = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.roll_no} - {self.name}"
