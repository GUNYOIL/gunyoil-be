from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from config.api import success_response
from .models import Exercise
from .serializers import ExerciseSerializer


class ExerciseListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Exercise.objects.all()

        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category.upper())

        target_muscle = request.query_params.get('target_muscle')
        if target_muscle:
            queryset = queryset.filter(target_muscle__icontains=target_muscle)

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)

        serializer = ExerciseSerializer(queryset, many=True)
        return success_response(serializer.data)
