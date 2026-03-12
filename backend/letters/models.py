from django.db import models
from students.models import Student
from users.models import User

class Letter(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending HOD Approval'),
        ('hod_approved', 'HOD Approved'),
        ('hod_rejected', 'HOD Rejected'),
        ('final_approved', 'Principal Approved'),
        ('final_rejected', 'Principal Rejected'),
    )

    LETTER_TYPE_CHOICES = (
        ('bonafide', 'Bonafide Certificate'),
        ('noc', 'No Objection Certificate'),
        ('internship', 'Internship Permission'),
        ('academic', 'Academic Recommendation'),
        ('hackathon', 'Hackathon Permission'),
        ('other', 'Other'),
    )

    student_roll = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='letters', db_column='student_roll')
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='requested_letters')
    letter_type = models.CharField(max_length=50, choices=LETTER_TYPE_CHOICES, default='bonafide')
    purpose = models.CharField(max_length=255)
    details = models.TextField(blank=True, default='')
    content = models.TextField()

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # HOD approval
    hod_approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hod_approved_letters')
    hod_notes = models.TextField(blank=True, default='')
    hod_approved_at = models.DateTimeField(null=True, blank=True)

    # Principal approval
    principal_approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='principal_approved_letters')
    principal_notes = models.TextField(blank=True, default='')
    principal_approved_at = models.DateTimeField(null=True, blank=True)

    pdf_url = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student_roll_id} - {self.letter_type} - {self.status}"
