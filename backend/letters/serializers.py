from rest_framework import serializers
from .models import Letter


class LetterSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = Letter
        fields = [
            'id', 'student_roll_id', 'student_name', 'letter_type', 'purpose',
            'details', 'content', 'status', 'status_label',
            'hod_notes', 'hod_approved_at',
            'principal_notes', 'principal_approved_at',
            'pdf_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'student_name', 'status_label']

    def get_student_name(self, obj):
        try:
            return obj.student_roll.name
        except Exception:
            return str(obj.student_roll_id)

    def get_status_label(self, obj):
        labels = {
            'pending': 'Awaiting HOD',
            'hod_approved': 'HOD Approved - Awaiting Principal',
            'hod_rejected': 'Rejected by HOD',
            'final_approved': 'Fully Approved',
            'final_rejected': 'Rejected by Principal',
        }
        return labels.get(obj.status, obj.status)
