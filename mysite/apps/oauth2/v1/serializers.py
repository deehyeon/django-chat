from rest_framework import serializers

class MessageSerializer(serializers.Serializer):
    """단순 메시지 응답"""
    message = serializers.CharField()

class TokenPairSerializer(serializers.Serializer):
    """액세스/리프레시 토큰 쌍"""
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()

class RefreshTokenRequestSerializer(serializers.Serializer):
    """리프레시 토큰으로 재발급 요청"""
    refresh_token = serializers.CharField()

class EmailAuthRequestSerializer(serializers.Serializer):
    """이메일 인증 요청"""
    email = serializers.EmailField()

class EmailAuthResponseSerializer(serializers.Serializer):
    """이메일 인증 성공 응답"""
    message = serializers.CharField()
    email = serializers.EmailField()
    userName = serializers.CharField(allow_blank=True)
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()

class LogoutRequestSerializer(serializers.Serializer):
    """로그아웃(리프레시 토큰 무효화) 요청"""
    refresh_token = serializers.CharField()

# OAuth 콜백(소셜) 요청/응답
class OAuthCallbackRequestSerializer(serializers.Serializer):
    """OAuth2 콜백 요청 바디"""
    code = serializers.CharField(help_text="Provider가 전달한 authorization code")
    # 문자열(JSON) 또는 객체가 올 수 있으므로 JSONField를 사용
    state = serializers.JSONField(required=False, help_text="문자열(JSON) 또는 객체. {'redirect_url': '...'} 형태를 기대")

class OAuthCallbackResponseSerializer(serializers.Serializer):
    """OAuth2 콜백 성공 응답"""
    email = serializers.EmailField()
    userName = serializers.CharField(allow_blank=True)
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    redirect_url = serializers.CharField(allow_blank=True)

# 내부 플로우(토큰 교환, 사용자 정보 조회) 문서화를 위한 스키마
class OAuthTokenExchangeRequestSerializer(serializers.Serializer):
    """Provider 토큰 엔드포인트로의 교환 요청 구조(문서용)"""
    grant_type = serializers.CharField(default="authorization_code")
    code = serializers.CharField()
    redirect_uri = serializers.URLField()
    client_id = serializers.CharField()
    client_secret = serializers.CharField()

class OAuthTokenExchangeResponseSerializer(serializers.Serializer):
    """Provider 토큰 응답 구조(문서용)"""
    access_token = serializers.CharField()
    token_type = serializers.CharField(required=False)
    expires_in = serializers.IntegerField(required=False)
    refresh_token = serializers.CharField(required=False)
    scope = serializers.CharField(required=False)

class OAuthProviderUserInfoSerializer(serializers.Serializer):
    """Provider 사용자 정보 구조(문서용)"""
    email = serializers.EmailField(allow_null=True, required=False)
    name = serializers.CharField(allow_blank=True, allow_null=True, required=False)

# 에러 응답 전용(필요 시 별도의 이름으로 구분해서 사용)
class BadRequestSerializer(serializers.Serializer):
    message = serializers.CharField()

class UnauthorizedSerializer(serializers.Serializer):
    message = serializers.CharField()

class ServerErrorSerializer(serializers.Serializer):
    message = serializers.CharField()