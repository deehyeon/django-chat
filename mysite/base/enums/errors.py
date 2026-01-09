# -- 회원 가입
# 이메일 형식이 올바르지 않음
E001_INVALID_EMAIL_FORMAT = {
    "message": "이메일 형식이 올바르지 않습니다",
    "error_code": "E0010001",
}
# 이메일 인증이 완료되지 않음
E001_EMAIL_NOT_VERIFIED = {
    "message": "회원 가입을 실패하였습니다",
    "error_code": "E0010002",
}
# 이미 사용 중인 이메일
E001_EMAIL_ALREADY_IN_USE = {
    "message": "회원 가입을 실패하였습니다",
    "error_code": "E0010003",
}
# 비밀번호 형식이 올바르지 않음
E001_INVALID_PASSWORD = {
    "message": "비밀번호는 6자 이상 30자 이하의 영문, 숫자 조합이어야 합니다",
    "error_code": "E0010004",
}
# 비밀번호가 일치하지 않음
E001_PASSWORD_MISMATCH = {
    "message": "비밀번호가 일치하지 않습니다",
    "error_code": "E0010005",
}

# -- 이메일 검증
# 해시된 이메일 형식이 올바르지 않음
E002_INVALID_HASHED_EMAIL_FORMAT = {
    "message": "이메일 검증을 실패하였습니다",
    "error_code": "E0020001",
}
# 이메일 검증 토큰이 올바르지 않음
E002_INVALID_VERIFICATION_TOKEN = {
    "message": "이메일 검증을 실패하였습니다",
    "error_code": "E0020002",
}
# 캐시에 인증 정보 없음
E002_VERIFICATION_INFO_NOT_FOUND = {
    "non_field": {
        "message": "이메일 검증을 실패하였습니다",
        "error_code": "E0020003",
    }
}
# 이미 인증된 이메일 주소
E002_EMAIL_ALREADY_VERIFIED = {
    "non_field": {
        "message": "이메일 검증을 실패하였습니다",
        "error_code": "E0020004",
    }
}
# 토큰이 저장되어있지 않거나 일치하지 않음
E002_VERIFICATION_TOKEN_NOT_MATCH = {
    "non_field": {
        "message": "이메일 검증을 실패하였습니다",
        "error_code": "E0020005",
    }
}

# -- 로그인
# 비밀번호 형식이 올바르지 않음
E003_INVALID_PASSWORD = {
    "non_field": {
        "message": "비밀번호가 일치하지 않습니다",
        "error_code": "E0030001",
    }
}
# 이메일 인증이 완료되지 않음
E003_EMAIL_NOT_VERIFIED = {
    "non_field": {
        "message": "이메일 인증을 완료해주세요",
        "error_code": "E0030002",
    }
}
# 프로필이 등록되어 있어야 로그인 가능
E003_PROFILE_NOT_FOUND = {
    "non_field": {
        "message": "프로필이 등록되어 있지 않습니다",
        "error_code": "E0030004",
    }
}
# 리프래시 토큰 재발급 실패
E003_REFRESH_TOKEN_FAILED = {
    "message": "리프래시 토큰 재발급에 실패하였습니다",
    "error_code": "E0030003",
}
# 토큰이 유효하지 않음
E003_INVALID_REFRESH_TOKEN = {
    "message": "토큰이 유효하지 않습니다",
    "error_code": "E0030005",
}
# 블랙리스트 처리 실패
E003_BLACKLIST_FAILED = {
    "message": "블랙리스트 처리에 실패하였습니다",
    "error_code": "E0030006",
}
# 사용자를 찾을 수 없음
E003_USER_NOT_FOUND = {
    "message": "사용자를 찾을 수 없습니다",
    "error_code": "E0030007",
}

# -- 비밀번호 초기화
# 해시된 이메일 형식이 올바르지 않음
E004_INVALID_HASHED_EMAIL_FORMAT = {
    "message": "이메일 검증을 실패하였습니다",
    "error_code": "E0040001",
}
# 이메일 검증 토큰이 올바르지 않음
E004_INVALID_VERIFICATION_TOKEN = {
    "message": "이메일 검증을 실패하였습니다",
    "error_code": "E0040002",
}
# 캐시에 인증 정보 없음
E004_VERIFICATION_INFO_NOT_FOUND = {
    "non_field": {
        "message": "이메일 검증을 실패하였습니다",
        "error_code": "E0040003",
    }
}
# 토큰이 저장되어있지 않거나 일치하지 않음
E004_VERIFICATION_TOKEN_NOT_MATCH = {
    "non_field": {
        "message": "이메일 검증을 실패하였습니다",
        "error_code": "E0040005",
    }
}

# -- 프로필
# 닉네임 길이가 맞지 않음
E008_INVALID_NICKNAME_LENGTH = {
    "message": "닉네임은 2자 이상 30자 이하로 설정해야 합니다",
    "error_code": "E0080001",
}
# 시작과 끝 공백 검사
E008_INVALID_NICKNAME_SPACING = {
    "message": "닉네임의 시작과 끝에 공백을 사용할 수 없습니다",
    "error_code": "E0080002",
}
# 연속 공백 검사
E008_INVALID_NICKNAME_CONSECUTIVE_SPACES = {
    "message": "닉네임에 연속된 공백을 사용할 수 없습니다",
    "error_code": "E0080003",
}
# 닉네임 정규식 검사
E008_INVALID_NICKNAME_FORMAT = {
    "message": "닉네임은 한글, 영어, 숫자, 특수문자(-_.+=^!)로만 구성되어야 합니다",
    "error_code": "E0080004",
}
# 별도로 정의한 금지된 단어 검사
E008_NICKNAME_CONTAINS_FORBIDDEN_WORD = {
    "message": "닉네임에 금지된 단어가 포함되어 있습니다",
    "error_code": "E0080005",
}
# 비속어 검사
E008_NICKNAME_CONTAINS_PROFANITY = {
    "message": "닉네임에 비속어가 포함되어 있습니다",
    "error_code": "E0080006",
}
