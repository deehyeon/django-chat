"""
JWT 토큰 생성 및 검증 유틸리티
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
import logging
from django.conf import settings
from apps.account.models import CustomUser
from .redis_client import get_redis_client


logger = logging.getLogger(__name__)


def generate_jwt_tokens(user: CustomUser) -> Dict[str, str]:
    """
    Access Token과 Refresh Token을 생성합니다.

    Args:
        user: CustomUser 인스턴스

    Returns:
        dict: {'access_token': str, 'refresh_token': str}
    """
    now = datetime.utcnow()

    # Access Token 페이로드 (15분 만료)
    access_token_payload = {
        'user_id': user.id,
        'email': user.email,
        'exp': now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        'iat': now,
        'type': 'access'
    }

    # Refresh Token 페이로드 (7일 만료)
    refresh_token_payload = {
        'user_id': user.id,
        'email': user.email,
        'exp': now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        'iat': now,
        'type': 'refresh'
    }

    # JWT 토큰 생성
    access_token = jwt.encode(
        access_token_payload,
        settings.SECRET_KEY,
        algorithm='HS256'
    )

    refresh_token = jwt.encode(
        refresh_token_payload,
        settings.SECRET_KEY,
        algorithm='HS256'
    )

    # Redis에 Refresh Token 저장
    try :
        redis = get_redis_client()
        redis_key = f"jwt:refresh:{user.id}"
        redis_ttl = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # 초 단위

        redis.setex(redis_key, redis_ttl, refresh_token)
    except Exception as e:
        logger.error(f"Redis에 Refresh Token 저장 실패: {e}")

    return {
        'access_token': access_token,
        'refresh_token': refresh_token
    }

def verify_access_token(token: str) -> Optional[Dict]:
    """
    Access Token을 검증하고 페이로드를 반환합니다.

    Args:
        token: Access Token 문자열

    Returns:
        dict: 토큰 페이로드 (검증 성공 시), None (실패 시)
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=['HS256']
        )

        # 토큰 타입 확인
        if payload.get('type') != 'access':
            return None

        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("Access Token이 만료되었습니다.")
    except jwt.InvalidTokenError as e:
        logger.debug(f"Access Token이 유효하지 않습니다: {e}")

def verify_refresh_token(refresh_token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=['HS256']
        )

        if payload.get("type") != "refresh":
            return None

        user_id = payload["user_id"]

        redis = get_redis_client()
        redis_key = f"jwt:refresh:{user_id}"
        stored_token = redis.get(redis_key)

        # Redis에 없거나 불일치 -> 무효
        if not stored_token or stored_token != refresh_token:
            logger.warning("Redis Refresh Token 불일치 또는 없음")
            return None
        return payload

    except jwt.ExpiredSignatureError:
        logger.debug("Refresh Token이 만료되었습니다.")
    except jwt.InvalidTokenError as e:
        logger.debug(f"Refresh Token이 유효하지 않습니다: {e}")
    return None

def refresh_access_token(refresh_token: str) -> Optional[Dict[str, str]]:
    """
    Refresh Token을 사용하여 새로운 Access Token을 발급합니다.

    Args:
        refresh_token: Refresh Token 문자열

    Returns:
        dict: {'access_token': str, 'refresh_token': str} (성공 시), None (실패 시)
    """
    # Refresh Token 검증
    payload = verify_refresh_token(refresh_token)

    if not payload:
        return None

    # 사용자 조회
    try:
        user = CustomUser.objects.get(id=payload['user_id'])
    except CustomUser.DoesNotExist:
        return None

    # 기존 Refresh Token 삭제
    try:
        redis = get_redis_client()
        redis_key = f"jwt:refresh:{user.id}"
        redis.delete(redis_key)
    except Exception:
        pass

    # 새로운 토큰 생성
    return generate_jwt_tokens(user)

def logout(user_id: int) -> bool:
    try:
        redis = get_redis_client()
        redis_key = f"jwt:refresh:{user_id}"
        redis.delete(redis_key)
        return True
    except Exception as e:
        logger.error(f"로그아웃 처리 중 오류 발생: {e}")
        return False

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

    try:
        user = CustomUser.objects.get(id=payload['user_id'])
        return user
    except CustomUser.DoesNotExist:
        return None

