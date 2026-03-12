from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from .models import Exam, ExamResult
from .serializers import ExamSerializer, ExamResultSerializer
from rest_framework.permissions import IsAuthenticated

class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        department = self.request.query_params.get('department')
        semester = self.request.query_params.get('semester')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if department:
            qs = qs.filter(course__department__iexact=department)
        if semester:
            qs = qs.filter(course__semester=semester)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
            
        return qs.select_related('course').order_by('date', 'start_time')

    @action(detail=False, methods=['get'])
    def available_rooms(self, request):
        date = request.query_params.get('date')
        if not date:
            return Response({'error': 'Date is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Simple mock logic for available rooms
        booked_exams = Exam.objects.filter(date=date)
        booked_rooms = [exam.room for exam in booked_exams if exam.room]
        
        all_rooms = ['Room A', 'Room B', 'Room C']
        available_rooms = [room for room in all_rooms if room not in booked_rooms]
        
        return Response({'available_rooms': available_rooms})

    @action(detail=False, methods=['get'])
    def conflicts(self, request):
        """
        Identify overlapping exams. We consider an overlap if two exams:
        - Are on the same date
        - Have overlapping start_time/end_time
        - Share either the exact same room, OR the same department & semester (conflict for students).
        """
        conflicts = []
        exams = list(self.get_queryset())
        
        for i in range(len(exams)):
            for j in range(i + 1, len(exams)):
                e1, e2 = exams[i], exams[j]
                
                # Must be same date with valid times
                if e1.date != e2.date or not e1.start_time or not e1.end_time or not e2.start_time or not e2.end_time:
                    continue
                    
                # Time overlap check: start1 < end2 AND start2 < end1
                if e1.start_time < e2.end_time and e2.start_time < e1.end_time:
                    
                    is_room_conflict = (e1.room and e2.room and e1.room.lower() == e2.room.lower())
                    
                    is_student_conflict = (
                        e1.course.department and e2.course.department and 
                        e1.course.department.lower() == e2.course.department.lower() and
                        e1.course.semester == e2.course.semester and
                        e1.course.semester is not None
                    )
                    
                    if is_room_conflict or is_student_conflict:
                        reason = "Room overlap" if is_room_conflict else "Student schedule clash (same dept & semester)"
                        if is_room_conflict and is_student_conflict: reason = "Room & Student clash"
                        
                        conflicts.append({
                            'exam1': ExamSerializer(e1).data,
                            'exam2': ExamSerializer(e2).data,
                            'reason': reason
                        })
                        
        return Response(conflicts)

class ExamResultViewSet(viewsets.ModelViewSet):
    queryset = ExamResult.objects.all()
    serializer_class = ExamResultSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def top_students(self, request):
        course_id = request.query_params.get('course_id')
        if not course_id:
            return Response({'error': 'course_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        results = ExamResult.objects.filter(exam__course_id=course_id).order_by('-marks')[:10]
        serializer = self.get_serializer(results, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='pass-percentages')
    def pass_percentages(self, request):
        """Return pass percentage across departments."""
        results = ExamResult.objects.values('exam__course__department').annotate(
            total=Count('id'),
            passed=Count('id', filter=Q(marks__gte=40))
        )
        
        formatted_data = []
        for r in results:
            dept = r['exam__course__department'] or 'Unknown'
            total = r['total']
            passed = r['passed']
            pass_rate = round((passed / total * 100), 1) if total > 0 else 0
            formatted_data.append({
                'department': dept,
                'passRate': pass_rate,
                'total': total
            })
            
        return Response(formatted_data)
