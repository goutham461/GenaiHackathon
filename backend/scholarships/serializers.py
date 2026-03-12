from rest_framework import serializers
from .models import ScholarshipScheme

class ScholarshipSchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScholarshipScheme
        fields = '__all__'
