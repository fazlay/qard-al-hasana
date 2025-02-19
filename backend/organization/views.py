from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.generics import (
    CreateAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError


from peoples.models import Staff

# from transaction.models import Savings, Loan

from .serializers import (
    LoginSerializer,
    TeamDetailSerializer,
    UserSerializer,
    UserSerilizerWithToken,
    MyRefreshSerializer,
    TeamSerializer,
    StaffListSerializer,
    BranchListSerializer,
    LogoutSerializer,
)


from .models import Team, Branch
from .paginations.paginations import CommonPageNumberPagination


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer


class LogoutView(APIView):
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh = RefreshToken(serializer.validated_data["refresh"])
            print(refresh)
            refresh.blacklist()
        except TokenError:
            pass

        return Response({"detail": "Successfully logged out."})


class RefreshTokenView(TokenRefreshView):
    serializer_class = MyRefreshSerializer


class RegisterView(CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerilizerWithToken(user, many=False).data)


class TeamCreateListApiView(ListCreateAPIView):
    queryset = Team.objects.all().order_by("-id")
    permission_classes = [IsAuthenticated]
    serializer_class = TeamSerializer
    filterset_fields = ["owner", "branch"]

    def perform_create(self, serializer):
        serializer.save(branch=serializer.validated_data["owner"].branch)


class TeamRetriveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TeamDetailSerializer

    def get_object(self):
        return get_object_or_404(Team, id=self.kwargs["pk"])


class StaffReadOnlyModelViewSet(viewsets.ReadOnlyModelViewSet):
    """provides only list and retrieve actions"""

    queryset = Staff.objects.all()
    serializer_class = StaffListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CommonPageNumberPagination

    def get_queryset(self):
        return self.queryset.filter(user__branch=self.request.user.branch)


class BranchReadOnlyModelViewSet(viewsets.ReadOnlyModelViewSet):
    """provides only list and retrieve actions"""

    queryset = Branch.objects.all()
    serializer_class = BranchListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CommonPageNumberPagination

    def get_queryset(self):
        # return self.queryset.filter(id=self.request.user.branch.id).annotate(
        return self.queryset.annotate(
            total_deposit=Sum(
                "basemodel__savings__amount",
                filter=Q(basemodel__savings__transaction_type="deposit"),
                default=0,
            )
            - Sum(
                "basemodel__savings__amount",
                filter=Q(basemodel__savings__transaction_type="withdraw"),
                default=0,
            ),
            total_due_loan=Sum(
                "basemodel__loan__total_due",
                filter=Q(basemodel__loan__is_paid=False),
                default=0
            ),
            total_income=Sum(
                'basemodel__generaltransaction__amount',
                filter=Q(basemodel__generaltransaction__transaction_type='income'),
                default=0
            ),
            total_expense=Sum(
                'basemodel__generaltransaction__amount',
                filter=Q(basemodel__generaltransaction__transaction_type='expense'),
                default=0
            ),
        )
