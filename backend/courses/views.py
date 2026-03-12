from django.db.models import Avg, Count
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Course
from .serializers import CourseSerializer
from rest_framework.permissions import IsAuthenticated

class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Course.objects.all()
        dept = self.request.query_params.get('department')
        sem = self.request.query_params.get('semester')
        course_type = self.request.query_params.get('type')
        credits_val = self.request.query_params.get('credits')

        if dept:
            qs = qs.filter(department__iexact=dept)
        if sem:
            qs = qs.filter(semester=sem)
        if course_type:
            qs = qs.filter(type__iexact=course_type)
        if credits_val:
            qs = qs.filter(credits=credits_val)

        return qs

    @action(detail=False, methods=['GET'])
    def stats(self, request):
        total = Course.objects.count()
        avg_credits = Course.objects.aggregate(Avg('credits'))['credits__avg'] or 0
        
        dept_counts = Course.objects.values('department').annotate(count=Count('id')).order_by('-count')
        
        return Response({
            'total_courses': total,
            'average_credits': round(avg_credits, 1),
            'department_distribution': list(dept_counts)
        })
