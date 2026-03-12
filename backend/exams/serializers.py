from rest_framework import serializers
from .models import Exam, ExamResult

class ExamSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    department = serializers.CharField(source='course.department', read_only=True)
    semester = serializers.IntegerField(source='course.semester', read_only=True)
    
    class Meta:
        model = Exam
        fields = '__all__'

class ExamResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamResult
        fields = '__all__'
