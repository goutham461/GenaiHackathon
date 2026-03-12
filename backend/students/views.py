from rest_framework import viewsets
from .models import Student
from .serializers import StudentSerializer
from rest_framework.permissions import IsAuthenticated

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Student.objects.all()
        dept = self.request.query_params.get('dept', None)
        year = self.request.query_params.get('year', None)
        if dept:
            queryset = queryset.filter(department=dept)
        if year:
            queryset = queryset.filter(year=year)
        return queryset
