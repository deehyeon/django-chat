
import uuid
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

import jwt
from django.conf import settings
from django.core.cache import cache

from apps.user.models import CustomUser


# =========================
# 설정값 로더 (기본값 포함)
# =========================
def _get_setting(name: str, default: Any) -> Any:
    return getattr(settings, name, default)


JWT_ALGORITHM: str = _get_setting("JWT_ALGORITHM", "HS256")
JWT_SECRET: str = _get_setting("JWT_SECRET", settings.SECRET_KEY)
JWT_ISSUER: Optional[str] = _get_setting("JWT_ISSUER", None)
JWT_AUDIENCE: Optional[str] = _get_setting("JWT_AUDIENCE", None)

JWT_ACCESS_TTL: int = _get_setting("JWT_ACCESS_TTL", 60 * 15)          # 15분
JWT_REFRESH_TTL: int = _get_setting("JWT_REFRESH_TTL", 60 * 60 * 24 * 7)  # 7일

# 리프레시 토큰 회전/블랙리스트 옵션
JWT_REFRESH_ROTATE: bool = _get_setting("JWT_REFRESH_ROTATE", True)      # 재발급 시 리프레시도 회전
JWT_REFRESH_BLACKLIST: bool = _get_setting("JWT_REFRESH_BLACKLIST", True)# 로그아웃/회전시 기존 리프레시 블랙리스트

# 블랙리스트 캐시 키 prefix
REFRESH_BLACKLIST_PREFIX = _get_setting("JWT_REFRESH_BLACKLIST_PREFIX", "jwt:refresh:blacklist:")


# =========================
# 내부 유틸
# =========================
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _make_jwt(payload: Dict[str, Any], ttl_seconds: int) -> str:
    now = _utcnow()
    exp = now + timedelta(seconds=ttl_seconds)

    std_claims = {
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    if JWT_ISSUER:
        std_claims["iss"] = JWT_ISSUER
    if JWT_AUDIENCE:
        std_claims["aud"] = JWT_AUDIENCE

    to_encode = {**payload, **std_claims}
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_jwt(token: str, verify_exp: bool = True) -> Dict[str, Any]:
    options = {"verify_exp": verify_exp}
    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        issuer=JWT_ISSUER if JWT_ISSUER else None,
        audience=JWT_AUDIENCE if JWT_AUDIENCE else None,
        options=options,
    )


def _blacklist_key(jti: str) -> str:
    return f"{REFRESH_BLACKLIST_PREFIX}{jti}"


def _blacklist_refresh_token(jti: str, exp_ts: int) -> None:
    """
    리프레시 토큰 만료 시각까지 캐시에 블랙리스트 표시.
    캐시 TTL은 만료 시각 - 현재 시각(초)
    """
    ttl = max(exp_ts - int(time.time()), 1)
    cache.set(_blacklist_key(jti), True, ttl)


def _is_refresh_blacklisted(jti: str) -> bool:
    return bool(cache.get(_blacklist_key(jti)))


# =========================
# 공개 API
# =========================
def generate_jwt_tokens(user) -> Dict[str, str]:
    """
    주어진 사용자로 access/refresh 페어를 생성.
    payload에는 최소한 식별 가능한 클레임(sub, uid, email)을 포함.
    """
    user_id = getattr(user, "id", None) or getattr(user, "pk", None)
    email = getattr(user, "email", None)
    username = getattr(user, "username", None)

    # access 토큰
    access_payload = {
        "type": "access",
        "sub": str(user_id),
        "uid": str(user_id),
        "email": email,
        "username": username,
    }
    access = _make_jwt(access_payload, JWT_ACCESS_TTL)

    # refresh 토큰
    refresh_payload = {
        "type": "refresh",
        "sub": str(user_id),
        "uid": str(user_id),
    }
    refresh = _make_jwt(refresh_payload, JWT_REFRESH_TTL)

    return {"access": access, "refresh": refresh}


def verify_refresh_token(refresh_token: str) -> Dict[str, Any]:
    """
    리프레시 토큰을 검증하고 payload를 반환.
    - exp/nbf/iat/iss/aud 검증
    - type = 'refresh' 확인
    - 블랙리스트 확인
    예외 발생 시 jwt.InvalidTokenError 계열 예외를 그대로 전달.
    """
    payload = _decode_jwt(refresh_token, verify_exp=True)

    if payload.get("type") != "refresh":
        raise jwt.InvalidTokenError("Not a refresh token.")

    jti = payload.get("jti")
    if JWT_REFRESH_BLACKLIST and jti and _is_refresh_blacklisted(jti):
        raise jwt.InvalidTokenError("Refresh token is blacklisted (logged out or rotated).")

    return payload

def verify_access_token(access_token: str) -> Optional[Dict[str, Any]]:
    """
        액세스 토큰을 검증하고 payload를 반환.
        - 유효하지 않거나 만료되면 None 반환 (뷰에서 다루기 편하게 예외 대신 None)
    """
    try:
        payload = _decode_jwt(access_token, verify_exp=True)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

    if payload.get("type") != "access":
        return None

    return payload


def refresh_access_token(refresh_token: str) -> Dict[str, str]:
    """
    리프레시 토큰으로 새 access 토큰을 발급.
    - ROTATE 설정이 True면, 새 refresh도 발급하고 기존 refresh는 블랙리스트 처리.
    - False면, 기존 refresh는 그대로 유지.
    반환: {"access": "...", "refresh": "...(선택적)"}
    """
    payload = verify_refresh_token(refresh_token)  # 검증 + 블랙리스트 체크
    user_id = payload.get("uid") or payload.get("sub")

    # 새 access 발급
    access_payload = {
        "type": "access",
        "sub": str(user_id),
        "uid": str(user_id),
    }
    new_access = _make_jwt(access_payload, JWT_ACCESS_TTL)

    result = {"access": new_access}

    # 리프레시 회전
    if JWT_REFRESH_ROTATE:
        # 기존 refresh 블랙리스트 처리
        if JWT_REFRESH_BLACKLIST and payload.get("jti") and payload.get("exp"):
            _blacklist_refresh_token(payload["jti"], payload["exp"])

        # 새 refresh 발급
        refresh_payload = {
            "type": "refresh",
            "sub": str(user_id),
            "uid": str(user_id),
        }
        new_refresh = _make_jwt(refresh_payload, JWT_REFRESH_TTL)
        result["refresh"] = new_refresh

    return result


def logout(refresh_token: str) -> None:
    """
    리프레시 토큰을 블랙리스트에 올려 무효화.
    이후 해당 refresh로 재발급 불가.
    """
    try:
        payload = _decode_jwt(refresh_token, verify_exp=True)
    except jwt.ExpiredSignatureError:
        # 이미 만료된 토큰이면 추가 조치 불필요
        return
    except jwt.InvalidTokenError:
        # 형식이 유효하지 않으면 무시(로그만 남기고 통과해도 됨)
        return

    if payload.get("type") != "refresh":
        # access 토큰을 넘긴 경우: 아무 처리 안 함(선택적으로 예외로 바꿀 수 있음)
        return

    if JWT_REFRESH_BLACKLIST and payload.get("jti") and payload.get("exp"):
        _blacklist_refresh_token(payload["jti"], payload["exp"])

def get_user_from_access_token(token: str) -> Optional[CustomUser]:
    """
    Access Token에서 사용자 정보를 추출합니다.

    Args:
        token: Access Token 문자열

    Returns:
        CustomUser 인스턴스 (성공 시), None (실패 시)
    """
    payload = verify_access_token(token)

    if not payload:
        return None

    user_id = payload.get("user_id") or payload.get("uid") or payload.get("sub")
    if not user_id:
        return None

    try:
        return CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return None
