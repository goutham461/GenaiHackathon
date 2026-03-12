from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count
from .models import AttendanceRecord
from .serializers import AttendanceRecordSerializer
from students.models import Student


def _calc_attendance(student, dept_filter=None):
    """Returns a dict with attendance stats for a student."""
    records = AttendanceRecord.objects.filter(roll_no=student)
    total = records.count()
    if total == 0:
        return None
    present = records.filter(status='present').count()
    pct = round(present / total * 100, 1)
    # Classes needed to reach 75%
    classes_needed = 0
    if pct < 75:
        # Solve: (present + x) / (total + x) = 0.75
        # present + x = 0.75 * total + 0.75 * x => 0.25x = 0.75*total - present
        need = max(0, int((0.75 * total - present) / 0.25) + 1)
        classes_needed = need
    return {
        'roll_no': student.roll_no,
        'name': student.name,
        'department': student.department,
        'year': student.year,
        'total_days': total,
        'present_days': present,
        'absent_days': total - present,
        'attendance_percentage': pct,
        'classes_needed': classes_needed,
        'status': 'CRITICAL' if pct < 65 else 'WARNING' if pct < 75 else 'SAFE',
    }


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
        try:
            student = Student.objects.get(roll_no=roll_no)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
        data = _calc_attendance(student)
        if not data:
            return Response({'roll_no': roll_no, 'percentage': 0, 'present_days': 0, 'total_days': 0, 'status': 'NO DATA'})

        # Also return recent 10 records
        recent = AttendanceRecord.objects.filter(roll_no=student).order_by('-date')[:10]
        data['recent_records'] = [{'date': str(r.date), 'status': r.status} for r in recent]
        return Response(data)

    @action(detail=False, methods=['get'])
    def low(self, request):
        """All students below a threshold (default 75%)."""
        threshold = float(request.query_params.get('threshold', 75.0))
        dept = request.query_params.get('department') or request.query_params.get('dept')

        qs = Student.objects.all()
        if dept:
            qs = qs.filter(department__iexact=dept)

        result = []
        for student in qs:
            data = _calc_attendance(student)
            if data and data['attendance_percentage'] < threshold:
                result.append(data)

        result.sort(key=lambda x: x['attendance_percentage'])
        return Response(result)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Aggregate attendance statistics for the dashboard."""
        dept = request.query_params.get('department')

        qs = Student.objects.all()
        if dept:
            qs = qs.filter(department__iexact=dept)

        total_students = qs.count()
        all_data = [_calc_attendance(s) for s in qs]
        all_data = [d for d in all_data if d]  # remove None

        if not all_data:
            return Response({'total': total_students, 'avg_pct': 0, 'warning': 0, 'critical': 0, 'safe': 0})

        avg_pct = round(sum(d['attendance_percentage'] for d in all_data) / len(all_data), 1)
        warning_count = sum(1 for d in all_data if d['status'] == 'WARNING')
        critical_count = sum(1 for d in all_data if d['status'] == 'CRITICAL')
        safe_count = sum(1 for d in all_data if d['status'] == 'SAFE')

        # Department breakdown
        dept_map = {}
        for d in all_data:
            dept_key = d['department'] or 'Unknown'
            if dept_key not in dept_map:
                dept_map[dept_key] = {'count': 0, 'sum_pct': 0, 'warning': 0, 'critical': 0}
            dept_map[dept_key]['count'] += 1
            dept_map[dept_key]['sum_pct'] += d['attendance_percentage']
            if d['status'] == 'WARNING':
                dept_map[dept_key]['warning'] += 1
            elif d['status'] == 'CRITICAL':
                dept_map[dept_key]['critical'] += 1

        dept_breakdown = [
            {
                'department': k,
                'count': v['count'],
                'avg_pct': round(v['sum_pct'] / v['count'], 1),
                'warning': v['warning'],
                'critical': v['critical'],
            }
            for k, v in dept_map.items()
        ]
        dept_breakdown.sort(key=lambda x: x['avg_pct'])

        return Response({
            'total': total_students,
            'tracked': len(all_data),
            'avg_pct': avg_pct,
            'warning': warning_count,
            'critical': critical_count,
            'safe': safe_count,
            'dept_breakdown': dept_breakdown,
        })
