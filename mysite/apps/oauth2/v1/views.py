from django.conf import settings                         # OAuth2 설정값 사용
from django.http import JsonResponse, HttpResponseRedirect # JSON 응답 반환                     # 클래스 기반 뷰
from django.utils.decorators import method_decorator     # 메서드에 데코레이터 적용
from django.views.decorators.csrf import csrf_exempt     # CSRF 검증 비활성화
from typing import Optional                              # 타입 헌팅
import secrets
from urllib.parse import urlencode

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework import permissions
from rest_framework.views import APIView

from apps.user.models import CustomUser               # 프로젝트의 커스텀 사용자 모델
from .serializers import *
from ..utils import (
    generate_jwt_tokens
)

import requests  # OAuth2 서버와 HTTP 통신
import json      # JSON 파싱/생성
import logging

logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# 1) OAuth 시작: 프론트가 POST로 호출 → 서버가 네이버로 리다이렉트
# ------------------------------------------------------------
@method_decorator(csrf_exempt, name="dispatch")  # 프론트 POST 리다이렉트 용도로 CSRF 비활성화
class NaverAuthStartView(APIView):
    """
    프론트의 POST 요청을 받아 네이버 OAuth 승인 URL을 생성하고 302 리다이렉트합니다.
    - 서버가 client_id/redirect_uri/state를 조합합니다.
    - state는 세션에 저장하여 콜백에서 검증합니다.
    """
    
    @extend_schema(
            tags=["OAuth2"],
            summary="네이버 OAuth 시작: 승인 URL 생성 후 302 리다이렉트",
            description="프론트의 POST 요청을 받아 서버가 state 발급 및 승인 URL을 구성, 네이버 인증 화면으로 리다이렉트합니다.",
            examples=[OpenApiExample("시작", value={}, request_only=True)],
            responses={302: OpenApiResponse(description="Redirect to Naver OAuth")}
        )
    def get(self, request, *args, **kwargs):
        # CSRF 방지용 state 생성 및 세션에 저장
        state = secrets.token_urlsafe(32)
        request.session["oauth_state"] = state

        # 네이버 authorize URL 구성
        params = {
            "response_type": "code",
            "client_id": settings.OAUTH2_CLIENT_ID,
            "redirect_uri": settings.OAUTH2_REDIRECT_URI,  # 네이버 콘솔 등록값과 정확히 일치해야 합니다.
            "state": state,
        }
        authorize_url = f"https://nid.naver.com/oauth2.0/authorize?{urlencode(params)}"

        # 브라우저를 네이버 로그인/동의 화면으로 이동
        return HttpResponseRedirect(authorize_url)


# ------------------------------------------------------------
# 2) 콜백: 네이버가 GET으로 code/state를 전달 → 서버가 토큰 교환 후 JWT 발급
# ------------------------------------------------------------
class NaverCallbackView(APIView):
    """
    네이버 콜백 엔드포인트 (GET)
    - 쿼리 스트링으로 전달되는 code/state를 읽습니다.
    - state를 세션에 저장된 값과 검증합니다.
    - code로 토큰 교환 → access_token으로 사용자 정보 조회 → 내부 사용자 upsert → 자체 JWT 발급
    - JSON 바디로 access_token/refresh_token을 반환합니다.
    """
    permission_classes = [permissions.AllowAny]

    
    @extend_schema(
            tags=["OAuth2"],
            summary="네이버 OAuth 콜백: code 교환 → 프로필 조회 → JWT 발급(JSON)",
            description=(
                "네이버가 전달한 code/state를 검증하고 access_token을 교환 후 "
                "프로필을 조회, 내부 사용자 upsert 및 JWT(access/refresh)를 JSON 바디로 반환합니다."
            ),
            responses={
                200: OpenApiResponse(description="로그인 성공 / JWT 반환"),
                400: OpenApiResponse(description="요청 파라미터/프로필 오류"),
                401: OpenApiResponse(description="토큰 교환 실패 또는 이메일 미제공"),
                403: OpenApiResponse(description="state 불일치"),
                500: OpenApiResponse(description="서버 내부 오류"),
            },
            examples=[
                OpenApiExample(
                    "성공 응답",
                    value={
                        "email": "user@example.com",
                        "userName": "홍길동",
                        "access_token": "jwt-access",
                        "refresh_token": "jwt-refresh",
                    },
                    response_only=True
                ),
                OpenApiExample(
                    "이메일 미제공",
                    value={"message": "email_missing", "next": "/api/oauth2/email-auth"},
                    response_only=True
                )
            ]
        )
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code")
        state = request.GET.get("state")

        if not code or not state:
            return JsonResponse({"message": "missing code/state"}, status=400)

        # 1) state 검증
        saved_state = request.session.pop("oauth_state", None)
        if not saved_state or saved_state != state:
            return JsonResponse({"message": "invalid_state"}, status=403)

        # 2) code → token 교환
        access_token = self._exchange_code_for_access_token(code)
        if not access_token:
            return JsonResponse({"message": "token_exchange_failed"}, status=401)

        # 3) 사용자 정보 조회 (네이버 /v1/nid/me)
        profile = self._fetch_naver_profile(access_token)
        if not profile:
            return JsonResponse({"message": "profile_request_failed"}, status=400)

        # 네이버 표준 응답 형태 처리
        if profile.get("resultcode") != "00":
            return JsonResponse({"message": "invalid_profile_response"}, status=400)

        resp = profile.get("response", {}) or {}
        email = resp.get("email")
        name = resp.get("name")
        naver_id = resp.get("id")

        if not email:
            return JsonResponse({"message": "email_missing", "next": "/api/oauth2/email-auth"}, status=401)

        # 4) 내부 사용자 upsert/매핑
        try:
            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={"username": name or (email.split("@")[0] if "@" in email else email)}
            )
            if name and user.username != name:
                user.username = name
                user.save(update_fields=["username"])
        except Exception as e:
            logger.exception("user upsert failed: %s", e)
            return JsonResponse({"message": "user_upsert_failed"}, status=500)

        # 5) 자체 JWT 발급 (이미 사용 중인 util 함수 활용)
        tokens = generate_jwt_tokens(user)
        if not tokens:
            return JsonResponse({"message": "jwt_issue_failed"}, status=500)

        # 6) JSON 반환 
        return JsonResponse({
            "email": user.email,
            "userName": user.username or "",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
        }, status=200)

    # --- 내부 헬퍼들 ---
    def _exchange_code_for_access_token(self, code: str) -> Optional[str]:
        """
        네이버 토큰 엔드포인트로 인증 코드 교환하여 access_token을 획득
        """
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.OAUTH2_CLIENT_ID,
            "client_secret": settings.OAUTH2_CLIENT_SECRET,
            "redirect_uri": settings.OAUTH2_REDIRECT_URI,
        }
        try:
            r = requests.post(
                settings.OAUTH2_TOKEN_ENDPOINT,  # 예: "https://nid.naver.com/oauth2.0/token"
                data=token_data,
                headers={"Accept": "application/json"},
                timeout=10
            )
            if r.status_code != 200:
                logger.error("token exchange failed: %s %s", r.status_code, r.text)
                return None
            j = r.json()
            if "error" in j:
                logger.error("token exchange error: %s", j.get("error_description"))
                return None
            return j.get("access_token")
        except requests.RequestException as e:
            logger.exception("token request exception: %s", e)
            return None

    def _fetch_naver_profile(self, access_token: str) -> Optional[dict]:
        """
        네이버 프로필 API 호출
        """
        try:
            r = requests.get(
                settings.OAUTH2_USER_INFO_ENDPOINT,  # 예: "https://openapi.naver.com/v1/nid/me"
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
                timeout=10
            )
            if r.status_code != 200:
                logger.error("profile request failed: %s %s", r.status_code, r.text)
                return None
            return r.json()
        except requests.RequestException as e:
            logger.exception("profile request exception: %s", e)
            return None