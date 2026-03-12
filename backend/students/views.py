from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Count, Q
from .models import Student
from .serializers import StudentSerializer


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Student.objects.all()
        params = self.request.query_params

        dept = params.get('department') or params.get('dept')
        year = params.get('year')
        gpa_gte = params.get('gpa_gte')
        gpa_lte = params.get('gpa_lte')
        join_year = params.get('join_year')
        name = params.get('name')
        search = params.get('search')

        if dept:
            queryset = queryset.filter(department__iexact=dept)
        if year:
            queryset = queryset.filter(year=year)
        if gpa_gte:
            queryset = queryset.filter(gpa__gte=float(gpa_gte))
        if gpa_lte:
            queryset = queryset.filter(gpa__lte=float(gpa_lte))
        if join_year:
            queryset = queryset.filter(join_year=join_year)
        if name:
            queryset = queryset.filter(name__icontains=name)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(roll_no__icontains=search) | Q(email__icontains=search)
            )

        return queryset

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Return aggregate statistics for the student dashboard."""
        from django.utils import timezone
        current_year = timezone.now().year

        total = Student.objects.count()
        avg_gpa = Student.objects.aggregate(avg=Avg('gpa'))['avg']
        new_this_year = Student.objects.filter(join_year=current_year).count()

        dept_breakdown = (
            Student.objects
            .values('department')
            .annotate(count=Count('roll_no'))
            .order_by('-count')
        )

        year_breakdown = (
            Student.objects
            .values('year')
            .annotate(count=Count('roll_no'))
            .order_by('year')
        )

        return Response({
            'total': total,
            'avg_gpa': round(float(avg_gpa), 2) if avg_gpa else 0,
            'new_this_year': new_this_year,
            'dept_breakdown': list(dept_breakdown),
            'year_breakdown': list(year_breakdown),
        })

    @action(detail=False, methods=['get'], url_path='enrollment-trends')
    def enrollment_trends(self, request):
        """Return year-wise enrollment trends for the analytics dashboard."""
        trends = (
            Student.objects
            .values('join_year')
            .annotate(students=Count('roll_no'))
            .order_by('join_year')
        )
        
        formatted_data = [
            {'year': str(t['join_year']) if t['join_year'] else 'Unknown', 'students': t['students']}
            for t in trends
        ]
        return Response(formatted_data)
