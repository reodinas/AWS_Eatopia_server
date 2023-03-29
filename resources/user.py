from flask import request
from flask_restful import Resource
from mysql.connector import Error
from email_validator import validate_email, EmailNotValidError
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, get_jwt_identity

from mysql_connection import get_connection
from utils import check_password, hash_password


class UserRegisterResource(Resource):

    # 회원가입 API
    def post(self):
        # {
        #     "email" : "aaa@naver.com",
        #     "password" : "1234",
        #     "nickname" : "홍길동",
        #     "phone" : "010-9999-9999"
        # }

        # 1. 클라이언트가 보낸 데이터를 받아준다.
        data = request.get_json()

        # 2. 이메일 주소 형식이 올바른지 확인한다.
        try:
            validate_email( data['email'] )


        except EmailNotValidError as e:
            print(str(e))
            return {'error':str(e)}, 400

        # 3. 비밀번호의 길이가 유효한지 체크한다.
        if len(data['password'] ) < 4 or len(data['password']) > 12:
            return {'error' : '비밀번호 길이 확인'}, 400

        # 4. 비밀번호를 암호화한다.
        hashed_password = hash_password(data['password'])
        # print(hashed_password)
        
        # 5. DB에 회원정보를 저장한다.
        try:
            connection = get_connection()
            query = '''insert into users
                    (email, password, nickname, phone)
                    values
                    (%s, %s, %s, %s);
                    '''
            record = (data['email'], hashed_password, data['nickname'], data['phone'])

            cursor = connection.cursor()
            cursor.execute(query, record)
            connection.commit()

            ### DB에 회원가입하여, insert 된 후에
            ### user 테이블의 id값을 가져오는 코드!
            userId = cursor.lastrowid

            cursor.close()
            connection.close()
        
        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return {'error' : str(e)}, 500


        ### userId를 바로 클라이언트에게 보내면 안되고,
        ### JWT로 암호화해서, 인증토큰을 보낸다.

        # create_access_token(userId,
        #                     expires_delta=datetime.timedelta(days=10))
        access_token = create_access_token(userId)

        return {'result' : 'success', 'access_token' : access_token}, 200
    

class UserLoginResource(Resource):

    # 로그인 API
    def post(self):
        # {
        #   "email" : "aaa@naver.com",
        #   "password" : "1234"
        # }

        # 1. 클라이언트가 보낸 데이터를 받아온다.
        data = request.get_json()

        # 2. DB로부터 해당 유저의 데이터를 가져온다.
        try:
            connection = get_connection()
            query = '''select *
                    from users
                    where email = %s;'''

            record = (data['email'], )

            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)

            result_list = cursor.fetchall()

            if not result_list:
                return {'error' : '회원가입한 사람이 아닙니다.'}, 400

            for row in result_list:
                row['createdAt'] = row['createdAt'].isoformat()

            cursor.close()
            connection.close()
        
        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return {'error' : str(e)}, 500

        # print(result_list)

        # 3. 비밀번호가 맞는지 확인한다.
        check = check_password(data['password'], result_list[0]['password'])

        if check == False:
            return {'error' : '비밀번호가 일치하지 않습니다.'}, 400

        # 4. JWT 토큰을 만들어서 클라이언트에게 보낸다.
        access_token = create_access_token( result_list[0]['id'] )

        return {'result' : 'success',
                'access_token' : access_token}, 200


# 로그아웃된 토큰을 저장할 set을 만든다.
jwt_blocklist = set()

class UserLogoutResource(Resource):

    # 로그아웃 API
    @jwt_required()
    def post(self):

        jti = get_jwt()['jti']

        jwt_blocklist.add(jti)

        return {'result' : 'success'}, 200


