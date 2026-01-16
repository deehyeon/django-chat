import jwt                  # 클래스 기반 뷰
from django.contrib.auth import authenticate
from django.utils.decorators import method_decorator     # 메서드에 데코레이터 적용
from django.views.decorators.csrf import csrf_exempt     # CSRF 검증 비활성화

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.views import APIView

from .serializers import *
from ..utils import (
    generate_jwt_tokens,
    refresh_access_token,
    verify_refresh_token,
    verify_access_token,
    get_user_from_access_token,
    logout,
)

class LoginView(APIView):
    """이메일+비밀번호 로그인 및 JWT 토큰 발급"""
    @extend_schema(
        tags=["User"],
        summary="이메일+비밀번호 로그인 (JWT 발급)",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(  # 성공 페이로드
                description="로그인 성공 및 토큰 발급",
                response=None,
                examples=[
                    OpenApiExample(
                        "성공 응답",
                        value={
                            "message": "사용자 인증 완료",
                            "email": "user@example.com",
                            "userName": "홍길동",
                            "access_token": "jwt-access-token",
                            "refresh_token": "jwt-refresh-token",
                        },
                        response_only=True,
                    )
                ],
            ),
            400: OpenApiResponse(MessageSerializer, description="요청 형식 오류"),
            401: OpenApiResponse(MessageSerializer, description="인증 실패"),
            403: OpenApiResponse(MessageSerializer, description="비활성화된 계정"),
            500: OpenApiResponse(MessageSerializer, description="토큰 생성 실패"),
        },
        examples=[
            OpenApiExample("요청 예시", value={"email": "user@example.com", "password": "secret"}, request_only=True),
        ],
        operation_id="auth_login",
    )
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"message": "요청 형식 오류"}, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(request, username=email, password=password)
        if not user:
            return Response(
                {"message": "이메일 또는 비밀번호가 올바르지 않습니다."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response({"message": "비활성화된 계정입니다."}, status=status.HTTP_403_FORBIDDEN)

        # JWT 토큰 생성
        tokens = generate_jwt_tokens(user)
        if not tokens:
            return Response({"message": "토큰 생성 실패"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        payload = {
            "message": "사용자 인증 완료",
            "email": user.email,
            "userName": user.username or "",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"]
        }

        return Response(payload, status=HTTP_200_OK)

class RefreshView(APIView):
    """Refresh Token을 사용하여 새로운 Access Token 발급"""
    @extend_schema(
        tags=["User"],
        summary="Refresh Token으로 새로운 Access Token 발급",
        request=RefreshTokenRequestSerializer,
        responses={
            200: OpenApiResponse(TokenPairSerializer, description="새 토큰 쌍 발급"),
            400: OpenApiResponse(MessageSerializer, description="요청 형식 오류"),
            401: OpenApiResponse(MessageSerializer, description="유효하지 않은 refresh_token"),
        },
        examples=[
            OpenApiExample(
                "요청 예시",
                value={"refresh_token": "your-refresh-token"},
                request_only=True,
            ),
            OpenApiExample(
                "성공 응답",
                value={"access_token": "new-access", "refresh_token": "new-refresh"},
                response_only=True,
            ),
        ],
        operation_id="auth_refresh",
    )
    def post(self, request, *args, **kwargs):
        serializer = RefreshTokenRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({"message": "요청 형식 오류"}, status=status.HTTP_400_BAD_REQUEST)

        refresh_token = serializer.validated_data.get("refresh_token")

        verify_refresh_token(refresh_token)
        tokens = refresh_access_token(refresh_token)

        return Response(
            {
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
            },
            status=status.HTTP_200_OK,
        )

class LogoutView(APIView):
    """로그아웃 - 토큰 무효화"""
    @extend_schema(
        tags=["User"],
        summary="로그아웃 (Refresh Token 무효화)",
        request=LogoutRequestSerializer,
        responses={
            200: OpenApiResponse(MessageSerializer, description="로그아웃 완료"),
            400: OpenApiResponse(MessageSerializer, description="요청 형식 오류"),
            401: OpenApiResponse(MessageSerializer, description="유효하지 않은 refresh_token"),
        },
        examples=[
            OpenApiExample("요청 예시", value={"refresh_token": "your-refresh-token"}, request_only=True),
            OpenApiExample("성공 응답", value={"message": "로그아웃 완료"}, response_only=True),
        ],
        operation_id="auth_logout",
    )
    def post(self, request, *args, **kwargs):
        serializer = LogoutRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"message": "요청 형식 오류"}, status=status.HTTP_400_BAD_REQUEST)

        refresh_token = serializer.validated_data.get("refresh_token")

        verify_refresh_token(refresh_token)
        logout(refresh_token)

        return Response({"message": "로그아웃 완료"}, status=status.HTTP_200_OK)



class UserInfoView(APIView):
    def get(self, request, *args, **kwargs):
        # 1) Authorization 헤더
        auth = request.headers.get("Authorization", "") or request.META.get("HTTP_AUTHORIZATION", "")
        token = None

        if isinstance(auth, str) and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()

        # 2) 쿼리스트링 fallback
        if not token:
            token = request.query_params.get("access_token")

        if not token:
            return Response({"message": "access_token이 필요합니다"}, status=status.HTTP_400_BAD_REQUEST)

        # 3) 토큰 검증 & 사용자 조회
        try:
            payload = verify_access_token(token)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            payload = None

        if not payload:
            return Response({"message": "유효하지 않은 access_token입니다"}, status=status.HTTP_401_UNAUTHORIZED)

        user = get_user_from_access_token(token)
        if not user:
            return Response({"message": "사용자를 찾을 수 없습니다"}, status=status.HTTP_404_NOT_FOUND)

        # 4) 필요한 필드만 반환
        return Response(
            {
                "id": user.pk,
                "email": getattr(user, "email", None),
            },
            status=status.HTTP_200_OK,
        )


