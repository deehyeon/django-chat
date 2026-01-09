"""
Redis 클라이언트 유틸리티
"""
import redis
import hashlib
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 클라이언트 싱글톤"""
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_client(self):
        """Redis 클라이언트 인스턴스 반환"""
        if self._client is None:
            try:
                # Redis 연결 설정
                redis_host = getattr(settings, 'REDIS_HOST', 'redis')
                redis_port = getattr(settings, 'REDIS_PORT', 6379)
                redis_db = getattr(settings, 'REDIS_JWT_DB', 1)  # JWT 전용 DB (0은 Celery에서 사용)
                redis_password = getattr(settings, 'REDIS_PASSWORD', None)

                # Redis 연결 옵션 구성
                redis_options = {
                    'host': redis_host,
                    'port': redis_port,
                    'db': redis_db,
                    'decode_responses': True,  # 자동으로 문자열 디코딩
                    'socket_connect_timeout': 5,
                    'socket_timeout': 5,
                    'retry_on_timeout': True
                }

                # 비밀번호가 있는 경우에만 추가
                if redis_password:
                    redis_options['password'] = redis_password

                self._client = redis.Redis(**redis_options)
                # 연결 테스트
                self._client.ping()
                logger.info(f"Redis 연결 성공: {redis_host}:{redis_port}/{redis_db}")
            except Exception as e:
                logger.error(f"Redis 연결 실패: {str(e)}")
                raise
        return self._client

    def close(self):
        """Redis 연결 종료"""
        if self._client:
            self._client.close()
            self._client = None


def get_redis_client() -> redis.Redis:
    """Redis 클라이언트 인스턴스 반환 (편의 함수)"""
    return RedisClient().get_client()


def hash_token(token: str) -> str:
    """토큰을 해시하여 키로 사용"""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

