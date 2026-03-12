from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Letter
from .serializers import LetterSerializer
from students.models import Student


class LetterViewSet(viewsets.ModelViewSet):
    serializer_class = LetterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'student':
            # Strategy 1: match by email
            students = Student.objects.filter(email=user.email)
            if students.exists():
                return Letter.objects.filter(student_roll__in=students)
            # Strategy 2: match by name (handles NULL email edge case)
            if user.full_name:
                students_by_name = Student.objects.filter(name__icontains=user.full_name.split()[0])
                if students_by_name.exists():
                    return Letter.objects.filter(student_roll__in=students_by_name)
            # Fallback: show letters requested by this user
            return Letter.objects.filter(requested_by=user)
        return Letter.objects.all()

    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        """Submit a new letter request."""
        student_roll = request.data.get('student_roll', '').upper()
        letter_type = request.data.get('letter_type', 'bonafide')
        purpose = request.data.get('purpose', '')
        details = request.data.get('details', '')

        if not student_roll or not purpose:
            return Response({'error': 'student_roll and purpose are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = Student.objects.get(roll_no=student_roll)
        except Student.DoesNotExist:
            return Response({'error': f'Student {student_roll} not found'}, status=status.HTTP_404_NOT_FOUND)

        content = (
            f"To Whom It May Concern,\n\n"
            f"This is to certify that {student.name} (Roll No: {student_roll}), "
            f"a student of {student.department} Department, Year {student.year}, "
            f"has requested a {letter_type.upper()} letter.\n\n"
            f"Purpose: {purpose}\n"
            f"Details: {details}\n\n"
            f"Kindly approve and issue the letter at the earliest.\n\n"
            f"Date: {timezone.now().strftime('%d %B %Y')}"
        )

        letter = Letter.objects.create(
            student_roll=student,
            requested_by=request.user,
            letter_type=letter_type,
            purpose=purpose,
            details=details,
            content=content,
            status='pending'
        )
        return Response(self.get_serializer(letter).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='hod-approve')
    def hod_approve(self, request, pk=None):
        """HOD approves a pending letter."""
        letter = self.get_object()
        if letter.status != 'pending':
            return Response({'error': f'Letter is already in {letter.status} state.'}, status=status.HTTP_400_BAD_REQUEST)

        notes = request.data.get('notes', 'Approved by HOD')
        letter.status = 'hod_approved'
        letter.hod_notes = notes
        letter.hod_approved_by = request.user
        letter.hod_approved_at = timezone.now()
        letter.save()
        return Response(self.get_serializer(letter).data)

    @action(detail=True, methods=['post'], url_path='hod-reject')
    def hod_reject(self, request, pk=None):
        """HOD rejects a pending letter."""
        letter = self.get_object()
        if letter.status != 'pending':
            return Response({'error': f'Letter is already in {letter.status} state.'}, status=status.HTTP_400_BAD_REQUEST)

        notes = request.data.get('notes', 'Rejected by HOD')
        letter.status = 'hod_rejected'
        letter.hod_notes = notes
        letter.hod_approved_by = request.user
        letter.hod_approved_at = timezone.now()
        letter.save()
        return Response(self.get_serializer(letter).data)

    @action(detail=True, methods=['post'], url_path='principal-approve')
    def principal_approve(self, request, pk=None):
        """Principal gives final approval."""
        letter = self.get_object()
        if letter.status != 'hod_approved':
            return Response({'error': 'Letter must be HOD-approved first.'}, status=status.HTTP_400_BAD_REQUEST)

        notes = request.data.get('notes', 'Approved by Principal')
        letter.status = 'final_approved'
        letter.principal_notes = notes
        letter.principal_approved_by = request.user
        letter.principal_approved_at = timezone.now()
        letter.save()
        return Response(self.get_serializer(letter).data)

    @action(detail=True, methods=['post'], url_path='principal-reject')
    def principal_reject(self, request, pk=None):
        """Principal rejects a letter."""
        letter = self.get_object()
        if letter.status != 'hod_approved':
            return Response({'error': 'Letter must be HOD-approved before principal review.'}, status=status.HTTP_400_BAD_REQUEST)

        notes = request.data.get('notes', 'Rejected by Principal')
        letter.status = 'final_rejected'
        letter.principal_notes = notes
        letter.principal_approved_by = request.user
        letter.principal_approved_at = timezone.now()
        letter.save()
        return Response(self.get_serializer(letter).data)

    @action(detail=False, methods=['get'], url_path='pending-hod')
    def pending_hod(self, request):
        """Get all letters awaiting HOD approval."""
        letters = Letter.objects.filter(status='pending')
        return Response(self.get_serializer(letters, many=True).data)

    @action(detail=False, methods=['get'], url_path='pending-principal')
    def pending_principal(self, request):
        """Get all HOD-approved letters awaiting Principal approval."""
        letters = Letter.objects.filter(status='hod_approved')
        return Response(self.get_serializer(letters, many=True).data)

    @action(detail=True, methods=['get'], url_path='track')
    def track(self, request, pk=None):
        letter = self.get_object()
        return Response({
            'id': letter.id,
            'status': letter.status,
            'status_label': self.get_serializer(letter).data['status_label'],
            'hod_notes': letter.hod_notes,
            'principal_notes': letter.principal_notes,
            'updated_at': letter.updated_at,
        })
