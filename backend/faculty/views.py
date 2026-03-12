from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Faculty, FacultyAssignment
from .serializers import FacultySerializer, FacultyAssignmentSerializer
from rest_framework.permissions import IsAuthenticated

class FacultyViewSet(viewsets.ModelViewSet):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'])
    def workload(self, request, pk=None):
        faculty = self.get_object()
        assignments = FacultyAssignment.objects.filter(faculty=faculty)
        # Calculate total workload hours (assuming each course implies a certain workload, simplifying for now)
        total_hours = faculty.workload_hours
        return Response({'faculty_id': faculty.id, 'workload_hours': total_hours, 'assignments_count': assignments.count()})

class FacultyAssignmentViewSet(viewsets.ModelViewSet):
    queryset = FacultyAssignment.objects.all()
    serializer_class = FacultyAssignmentSerializer
    permission_classes = [IsAuthenticated]
