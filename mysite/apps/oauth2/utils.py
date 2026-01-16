"""
JWT 토큰 생성 및 검증 유틸리티
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
import logging
from django.conf import settings
from apps.user.models import CustomUser
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

