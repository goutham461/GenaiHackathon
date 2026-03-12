from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from students.models import Student
from attendance.models import AttendanceRecord
from rest_framework.permissions import IsAuthenticated
import os

class WarningViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='student/(?P<roll_no>[^/.]+)')
    def student_risk(self, request, roll_no=None):
        try:
            student = Student.objects.get(roll_no=roll_no)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        records = AttendanceRecord.objects.filter(roll_no=student)
        total_days = 75 # Mock total days in a semester
        present_days = records.filter(status='present').count()
        current_percent = (present_days / total_days) * 100 if records.count() > 0 else 0
        
        target_percent = 75.0
        target_days = int((target_percent / 100) * total_days)
        days_needed = target_days - present_days
        
        if current_percent < 60:
            risk_level = 'HIGH RISK \U0001f534'
        elif current_percent < 75:
            risk_level = 'MEDIUM RISK \U0001f7e1'
        else:
            risk_level = 'SAFE \U0001f7e2'

        return Response({
            'roll_no': roll_no,
            'current_percent': round(current_percent, 2),
            'days_needed': max(0, days_needed),
            'risk_level': risk_level
        })

    @action(detail=False, methods=['post'], url_path='alert')
    def alert(self, request):
        roll_no = request.data.get('roll_no')
        message = request.data.get('message')

        if not roll_no or not message:
            return Response({'error': 'roll_no and message are required'}, status=status.HTTP_400_BAD_REQUEST)

        # MOCK TWILIO AND RESEND LOGIC
        print(f"Sending WhatsApp via Twilio to {roll_no}: {message}")
        print(f"Sending Email via Resend to mentor of {roll_no}: {message}")

        return Response({'status': 'Mock alerts triggered successfully'})
