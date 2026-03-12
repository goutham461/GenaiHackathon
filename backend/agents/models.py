from django.db import models
from django.conf import settings

class Agent(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    system_prompt = models.TextField()
    domain = models.CharField(max_length=50) # 'attendance', 'exam', 'student'
    tools = models.JSONField(default=list) # List of allowed tools
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class AgentAction(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    query = models.TextField(blank=True, null=True)
    sql_executed = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.agent} - {self.action} - {self.timestamp}"
