from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ScholarshipScheme
from .serializers import ScholarshipSchemeSerializer
from students.models import Student
from rest_framework.permissions import IsAuthenticated

class ScholarshipSchemeViewSet(viewsets.ModelViewSet):
    queryset = ScholarshipScheme.objects.all()
    serializer_class = ScholarshipSchemeSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='eligible/(?P<roll_no>[^/.]+)')
    def eligible(self, request, roll_no=None):
        try:
            student = Student.objects.get(roll_no=roll_no)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=404)

        # Mock logic for checking eligibility
        schemes = self.queryset.all()
        eligible_schemes = []
        for scheme in schemes:
            criteria = scheme.eligibility_criteria
            if criteria.get('income_max') and (student.annual_income or 0) > criteria['income_max']:
                continue
            if criteria.get('caste') and student.caste != criteria['caste']:
                continue
            if criteria.get('marks_min') and (student.marks_12th or 0) < criteria['marks_min']:
                continue
            eligible_schemes.append(self.get_serializer(scheme).data)

        return Response({'roll_no': roll_no, 'eligible_schemes': eligible_schemes})
