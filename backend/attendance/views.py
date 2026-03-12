from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import AttendanceRecord
from .serializers import AttendanceRecordSerializer
from students.models import Student
from rest_framework.permissions import IsAuthenticated

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = AttendanceRecord.objects.all()
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def mark(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(marked_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='student/(?P<roll_no>[^/.]+)')
    def student_attendance(self, request, roll_no=None):
        records = AttendanceRecord.objects.filter(roll_no=roll_no)
        total_days = records.count()
        if total_days == 0:
            return Response({'roll_no': roll_no, 'percentage': 0, 'present_days': 0, 'total_days': 0})
        
        present_days = records.filter(status='present').count()
        percentage = (present_days / total_days) * 100
        return Response({
            'roll_no': roll_no,
            'percentage': round(percentage, 2),
            'present_days': present_days,
            'total_days': total_days
        })

    @action(detail=False, methods=['get'])
    def low(self, request):
        threshold = float(request.query_params.get('threshold', 75.0))
        students = Student.objects.all()
        low_attendance_students = []
        
        for student in students:
            records = AttendanceRecord.objects.filter(roll_no=student)
            total_days = records.count()
            if total_days > 0:
                present_days = records.filter(status='present').count()
                percentage = (present_days / total_days) * 100
                if percentage < threshold:
                    low_attendance_students.append({
                        'roll_no': student.roll_no,
                        'name': student.name,
                        'percentage': round(percentage, 2)
                    })
        return Response(low_attendance_students)
