from rest_framework import serializers
from .models import Agent, AgentAction

class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = '__all__'

class AgentActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentAction
        fields = '__all__'
