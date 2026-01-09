from django.conf import settings                         # OAuth2 설정값 사용
from django.http import JsonResponse                     # JSON 응답 반환                     # 클래스 기반 뷰
from django.utils.decorators import method_decorator     # 메서드에 데코레이터 적용
from django.views.decorators.csrf import csrf_exempt     # CSRF 검증 비활성화
from typing import Optional                              # 타입 헌팅

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework import permissions
from rest_framework.views import APIView

from apps.account.models import CustomUser               # 프로젝트의 커스텀 사용자 모델
from .serializers import *
from ..utils import (
    generate_jwt_tokens,
    refresh_access_token,
    verify_refresh_token,
    logout,
)

import requests  # OAuth2 서버와 HTTP 통신
import json      # JSON 파싱/생성
import logging

logger = logging.getLogger(__name__)

# 클래서 테코레이터.
# CSRF 비활성화
# 클라이언트에서 POST 요청 시 CSRF 토큰 없이 호출 가능
@method_decorator(csrf_exempt, name='dispatch')
class CallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    # OAuth2 인증 코드를 받아 처리하는 메인 로직
    @extend_schema(
        tags=["OAuth2"],
        summary="OAuth2 콜백: 인증 코드로 토큰 교환 및 사용자 생성/조회",
        description=(
                "OAuth2 provider로부터 받은 authorization code와 optional state를 받아 "
                "프로바이더 액세스 토큰을 교환하고 사용자 정보를 조회한 뒤, 애플리케이션의 JWT 토큰을 발급합니다. "
                "state는 문자열(JSON string) 또는 객체(redirect_url 포함)로 올 수 있습니다."
        ),
        request=OAuthCallbackRequestSerializer,
        responses={
            200: OAuthCallbackResponseSerializer,
            400: BadRequestSerializer,
            401: UnauthorizedSerializer,
            500: ServerErrorSerializer,
        },
        examples=[
            OpenApiExample(
                name="state가 객체로 전달되는 경우",
                value={"code": "AUTH_CODE_123", "state": {"redirect_url": "https://app.example.com/after-login"}},
                request_only=True,
            ),
            OpenApiExample(
                name="state가 문자열(JSON)로 전달되는 경우",
                value={"code": "AUTH_CODE_123", "state": "{\"redirect_url\":\"https://app.example.com/after-login\"}"},
                request_only=True,
            ),
            OpenApiExample(
                name="성공 응답",
                value={
                    "email": "user@example.com",
                    "userName": "홍길동",
                    "access_token": "jwt-access-token",
                    "refresh_token": "jwt-refresh-token",
                    "redirect_url": "https://app.example.com/after-login",
                },
                response_only=True,
            ),
        ],
        # 글로벌 보안 스키마가 있다면 콜백은 인증 없이 접근 가능하도록 비워줍니다.
        operation_id="oauth2_callback",
    )
    def post(self, request, *args, **kwargs):
        try:
            # 요청 본문을 JSON으로 파싱
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"message" : "JSON 디코딩 에러"}, status=400)

        # 요청 데이터 추출
        code = data.get("code", "")    # OAuth2 인증 코드
        state = data.get("state", {})  # 추가 정보 포함
        if not code:
            return JsonResponse({"message": "code 정보 인식 실패"}, status=400)

        # state가 문자열이라면 JSON 반환
        if isinstance(state, str):
            try:
                state_json = json.loads(state)
            except json.JSONDecodeError:
                return JsonResponse({"message": "state JSON 디코딩 에러"}, status=400)

        else:
            state_json = state

        # redirect_url 추출
        redirect_url = state_json.get("redirect_url", "")

        # 1. 엑세스 토큰 요청
        # 인증 코드를 엑세스 토큰으로 교환
        access_token = self.request_access_token(code)

        if not access_token:
            logger.error("OAuth2 액세스 토큰 요청 실패")
            return JsonResponse({"message": "액세스 토큰 요청 실패"}, status = 401)

        # 2. 사용자 정보 요청
        user_info = self.request_user_info(access_token)
        if not user_info:
            logger.error("OAuth2 사용자 정보 요청 실패")
            return JsonResponse({"message": "사용자 정보 요청 실패"}, status=400)

        email = user_info.get("email", "")
        name = user_info.get("name", "")

        if not email:
            return JsonResponse({"message": "이메일 정보 추출 실패"}, status=401)

        # 3. 사용자 존재 여부 확인
        user = self.get_or_create_user(email, name)
        if user is None:
            logger.error(f"사용자 생성/조회 실패: {email}")
            return JsonResponse({"message": "사용자 생성 실패"}, status=500)

        # 4. JWT 토큰 생성
        tokens = generate_jwt_tokens(user)
        if not tokens:
            logger.error(f"JWT 토큰 생성 실패: {email}")
            return JsonResponse({"message": "토큰 생성 실패"}, status=500)

        # 5. 사용자 정보 반환
        response_data = {
            "email": email,
            "userName": name or user.username or "",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "redirect_url": redirect_url,
        }

        return JsonResponse(response_data, safe=False)

    def request_access_token(self, code: str) -> Optional[str]:
        """OAuth2 인증 코드를 액세스 토큰으로 교환"""
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.OAUTH2_REDIRECT_URI,
            "client_id": settings.OAUTH2_CLIENT_ID,
            "client_secret": settings.OAUTH2_CLIENT_SECRET,
        }

        try:
            response = requests.post(settings.OAUTH2_TOKEN_ENDPOINT, data=token_data, timeout=10)
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                logger.error(f"OAuth2 토큰 요청 실패: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            logger.error(f"OAuth2 토큰 요청 중 예외 발생: {str(e)}")

        return None

    def request_user_info(self, access_token: str) -> Optional[dict]:
        """액세스 토큰을 사용하여 사용자 정보 조회"""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(settings.OAUTH2_USER_INFO_ENDPOINT, headers=headers)

        if response.status_code == 200:
            data = response.json()
            profile = data.get("response", {})

            email = profile.get("email")
            name = profile.get("name")

            return {"email": email, "name": name}

        return None

    def get_or_create_user(self, email: str, name: str) -> Optional[CustomUser]:
        """사용자 조회 또는 생성 (CustomUser 사용)"""
        try:
            # 이메일로 사용자 조회
            user = CustomUser.objects.get(email=email)
            # 사용자명이 업데이트되지 않은 경우 업데이트
            if name and not user.username:
                user.username = name
                user.save(update_fields=['username'])
            return user
        except CustomUser.DoesNotExist:
            # 사용자가 없으면 생성 (OAuth2 로그인이므로 비밀번호 없음)
            try:
                user = CustomUser.objects.create_user(
                    email=email,
                    username=name or email.split("@")[0],
                    password=None  # OAuth2 인증이므로 비밀번호 없음
                )
                user.set_unusable_password()  # 비밀번호를 사용할 수 없도록 설정
                user.save()
                logger.info(f"새 사용자 생성: {email}")
                return user
            except Exception as e:
                logger.error(f"사용자 생성 중 예외 발생: {str(e)}")
                return None
        except Exception as e:
            logger.error(f"사용자 조회 중 예외 발생: {str(e)}")
            return None


@method_decorator(csrf_exempt, name="dispatch")
class RefreshTokenView(APIView):
    """Refresh Token을 사용하여 새로운 Access Token 발급"""

    @extend_schema(
        tags=["OAuth2"],
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
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"message": "JSON 디코딩 에러"}, status=400)

        refresh_token = data.get("refresh_token", "")

        if not refresh_token:
            return JsonResponse({"message": "refresh_token이 필요합니다"}, status=400)

        # Refresh Token으로 새로운 토큰 발급
        tokens = refresh_access_token(refresh_token)

        if not tokens:
            return JsonResponse({"message": "유효하지 않은 refresh_token입니다"}, status=401)

        return JsonResponse({
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
        }, safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class EmailAuthView(APIView):
    """이메일 기반 사용자 인증 및 JWT 토큰 발급"""

    @extend_schema(
        tags=["OAuth2"],
        summary="이메일로 사용자 인증 및 JWT 발급",
        request=EmailAuthRequestSerializer,
        responses={
            200: OpenApiResponse(EmailAuthResponseSerializer, description="인증 성공 및 토큰 발급"),
            400: OpenApiResponse(MessageSerializer, description="요청 형식 오류/유효하지 않은 이메일"),
            403: OpenApiResponse(MessageSerializer, description="등록되지 않은 사용자"),
            500: OpenApiResponse(MessageSerializer, description="토큰 생성 실패"),
        },
        examples=[
            OpenApiExample("요청 예시", value={"email": "user@example.com"}, request_only=True),
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
            ),
        ],
        operation_id="auth_email",
    )
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"message": "JSON 디코딩 에러"}, status=400)

        email = data.get("email", "")

        if not email:
            return JsonResponse({"message": "이메일이 필요합니다"}, status=400)

        # 이메일 형식 검증 (간단한 검증)
        if "@" not in email:
            return JsonResponse({"message": "유효하지 않은 이메일 형식입니다"}, status=400)

        try:
            user = CustomUser.objects.get(email=email)

        except CustomUser.DoesNotExist:
            return JsonResponse({"message": "등록되지 않은 사용자입니다. 관리자에게 문의바랍니다."}, status=403)

        # JWT 토큰 생성
        tokens = generate_jwt_tokens(user)
        if not tokens:
            logger.error(f"JWT 토큰 생성 실패: {email}")
            return JsonResponse({"message": "토큰 생성 실패"}, status=500)

        return JsonResponse({
            "message": "사용자 인증 완료",
            "email": user.email,
            "userName": user.username or "",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
        }, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(APIView):
    """로그아웃 - 토큰 무효화"""

    @extend_schema(
        tags=["OAuth2"],
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
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"message": "JSON 디코딩 에러"}, status=400)

        refresh_token = data.get("refresh_token", "")
        if not refresh_token:
            return JsonResponse({"message": "refresh_token이 필요합니다"}, status=400)

        payload = verify_refresh_token(refresh_token)
        if not payload:
            return JsonResponse({"message": "유효하지 않은 refresh_token입니다"}, status=401)

        logout(payload["user_id"])
        logger.info(f"사용자 로그아웃 완료: {payload['user_id']}")

        return JsonResponse({"message": "로그아웃 완료"}, status=200)