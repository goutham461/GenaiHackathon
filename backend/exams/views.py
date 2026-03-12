from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Exam, ExamResult
from .serializers import ExamSerializer, ExamResultSerializer
from rest_framework.permissions import IsAuthenticated

class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    permission_classes = [IsAuthenticated]

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
