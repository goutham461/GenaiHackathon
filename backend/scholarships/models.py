from django.db import models

class ScholarshipScheme(models.Model):
    name = models.CharField(max_length=255)
    eligibility_criteria = models.JSONField() # { "income_max": 200000, "caste": "SC", "marks_min": 85 }
    link = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
