from django.db import models

class Course(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=50, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    credits = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.code} - {self.name}"
