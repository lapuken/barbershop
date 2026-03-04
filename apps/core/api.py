from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.serializers import LoginSerializer
from apps.core.services import authenticate_and_login, logout_user
from apps.reports.services import build_dashboard_metrics


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, error = authenticate_and_login(
            request,
            serializer.validated_data["username"],
            serializer.validated_data["password"],
        )
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": user.id, "username": user.username, "role": user.role})


class LogoutAPIView(APIView):
    def post(self, request):
        logout_user(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DashboardReportView(APIView):
    def get(self, request):
        return Response(build_dashboard_metrics(request.user, getattr(request, "active_shop", None)))
