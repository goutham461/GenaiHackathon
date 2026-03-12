from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from exams.models import ExamResult
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal

class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='pass-rate')
    def pass_rate(self, request):
        dept = request.query_params.get('dept')
        sem = request.query_params.get('sem')
        
        # Simple mock logic for pass rate
        # Suppose a passing mark is > 40
        query = ExamResult.objects.all()
        if dept:
             query = query.filter(roll_no__department=dept)
        
        total = query.count()
        if total == 0:
             return Response({'pass_rate': 0})
        
        passed = query.filter(marks__gte=Decimal('40.00')).count()
        pass_rate = (passed / total) * 100
        
        return Response({'pass_rate': round(pass_rate, 2), 'dept': dept})

    @action(detail=False, methods=['get'], url_path='department-trends')
    def department_trends(self, request):
        years = request.query_params.get('years', '2023-2024')
        # Return mock data for charts
        return Response({
            'years': years,
            'data': [
                {'month': 'Jan', 'attendance': 85},
                {'month': 'Feb', 'attendance': 80},
                {'month': 'Mar', 'attendance': 78},
            ]
        })

    @action(detail=False, methods=['get'], url_path='generate-report')
    def generate_report(self, request):
        report_type = request.query_params.get('type', 'pdf')
        # Simulate report generation
        return Response({'download_url': f'/media/reports/report_mock.{report_type}'})
