from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Agent, AgentAction
from .serializers import AgentSerializer, AgentActionSerializer
from .utils.router import AgentRouter
from rest_framework.permissions import IsAuthenticated

class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def chat(self, request, pk=None):
        try:
            agent = self.get_object()
        except Agent.DoesNotExist:
            return Response({'error': 'Agent not found'}, status=status.HTTP_404_NOT_FOUND)

        message = request.data.get('message', '')
        if not message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)

        # In a real environment, the router would use the selected agent's prompt
        # Here we demonstrate the routing concept
        router = AgentRouter(user=request.user)
        response_text = router.route(message)

        # Log action
        AgentAction.objects.create(
            agent=agent,
            user=request.user,
            action='chat',
            query=message,
        )

        return Response({
            'agent': agent.name,
            'response': response_text,
            'message': message
        })

class AgentActionViewSet(viewsets.ModelViewSet):
    queryset = AgentAction.objects.all()
    serializer_class = AgentActionSerializer
    permission_classes = [IsAuthenticated]
