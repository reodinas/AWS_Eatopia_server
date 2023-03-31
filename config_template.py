class Config :
    # DB 관련
    HOST = ''
    DATABASE = ''
    DB_USER = ''
    DB_PASSWORD = ''
    SALT = '' # 비밀번호 암호화 시 추가 SALT

    # JWT 관련 변수 셋팅
    JWT_SECRET_KEY = ''
    JWT_ACCESS_TOKEN_EXPIRES = False 
    
    PROPAGATE_EXCEPTIONS = True # JWT 예외처리 메시지를 명시함

    # AWS 관련 키
    ACCESS_KEY = ''
    SECRET_ACCESS = ''

    # S3 버킷
    S3_BUCKET = ''
    # S3 Location
    S3_LOCATION = ''
    # 얼굴정보를 저장할 컬렉션ID
    COLLECTION_ID = ''