from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from users.views import UserViewSet
from students.views import StudentViewSet
from faculty.views import FacultyViewSet, FacultyAssignmentViewSet
from attendance.views import AttendanceViewSet
from exams.views import ExamViewSet, ExamResultViewSet
from courses.views import CourseViewSet
from analytics.views import AnalyticsViewSet
from student_warnings.views import WarningViewSet
from scholarships.views import ScholarshipSchemeViewSet
from letters.views import LetterViewSet
from agents.views import AgentViewSet, AgentActionViewSet

router = DefaultRouter()
router.register(r'auth', UserViewSet, basename='auth')
router.register(r'students', StudentViewSet, basename='students')
router.register(r'faculty', FacultyViewSet, basename='faculty')
router.register(r'faculty-assignments', FacultyAssignmentViewSet, basename='faculty-assignments')
router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'exams', ExamViewSet, basename='exams')
router.register(r'exam-results', ExamResultViewSet, basename='exam-results')
router.register(r'courses', CourseViewSet, basename='courses')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')
router.register(r'warnings', WarningViewSet, basename='warnings')
router.register(r'scholarships', ScholarshipSchemeViewSet, basename='scholarships')
router.register(r'letters', LetterViewSet, basename='letters')
router.register(r'agents', AgentViewSet, basename='agents')
router.register(r'agent-actions', AgentActionViewSet, basename='agent-actions')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]
