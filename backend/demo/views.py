"""The three unauthenticated demo endpoints (port of `Demo::SessionsController`).

All three are `AllowAny` with `authentication_classes = []`: the caller is a
guest with no session and no CSRF cookie, and DRF's `SessionAuthentication`
would enforce CSRF on the POST. This is safe only because the routes are not
registered at all unless `demo_mode.enabled()` — see `config/urls.py`.
"""

from __future__ import annotations

from django.contrib.auth import login as django_login
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_202_ACCEPTED
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from demo import personas
from demo.models import DemoSession
from demo.serializers import (
    DemoSessionCreateSerializer,
    DemoSessionSerializer,
    PersonaSerializer,
)
from demo.tasks import provision_demo_session_task


class DemoPersonaListView(APIView):
    """Lists the personas the picker offers."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "demo_personas"
    serializer_class = PersonaSerializer

    @extend_schema(responses={200: PersonaSerializer(many=True)})
    def get(self, request):
        return Response(PersonaSerializer(personas.all(), many=True).data)


class DemoSessionCreateView(APIView):
    """Creates a `pending` receipt and hands provisioning to the worker."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "demo_session_create"
    serializer_class = DemoSessionCreateSerializer

    @extend_schema(
        request=DemoSessionCreateSerializer,
        responses={202: DemoSessionSerializer},
    )
    def post(self, request):
        serializer = DemoSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = DemoSession.objects.create(persona=serializer.validated_data["persona"])
        # `ATOMIC_REQUESTS` wraps this view in a transaction, so enqueuing
        # directly would let the worker look for a row that has not been
        # committed yet and lose the session to a `DoesNotExist`.
        transaction.on_commit(
            lambda: provision_demo_session_task.delay(str(session.pk))
        )
        return Response(DemoSessionSerializer(session).data, status=HTTP_202_ACCEPTED)


class DemoSessionDetailView(APIView):
    """Reports session status and, once ready, signs the guest in.

    Sign-in lives on the poll rather than on a separate endpoint so that
    re-opening a session URL later just re-signs into the same workspace —
    provisioning never runs twice (paysys `SessionsController#show`).
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "demo_session_poll"
    serializer_class = DemoSessionSerializer

    @extend_schema(responses={200: DemoSessionSerializer})
    def get(self, request, pk):
        session = get_object_or_404(DemoSession, pk=pk)
        if session.provisioned:
            django_login(request, session.user)
        return Response(DemoSessionSerializer(session).data)
