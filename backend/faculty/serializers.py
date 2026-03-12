from rest_framework import serializers
from .models import Faculty, FacultyAssignment

class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = '__all__'

class FacultyAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacultyAssignment
        fields = '__all__'
