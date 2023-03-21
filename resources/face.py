from flask import request
from flask_restful import Resource
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from mysql.connector import Error
from flask_jwt_extended import jwt_required, get_jwt_identity
import base64

from config import Config
from mysql_connection import get_connection


class FaceResource(Resource):

    # 컬렉션에 얼굴 등록 API
    @jwt_required()
    def post(self):

        # 1. 클라이언트로부터 데이터를 받아온다.
        # form-data
        # -photo : file

        if 'photo' not in request.files:
            return {'error' : '파일을 업로드 하세요.'}, 400
        
        file = request.files['photo']

        userId = get_jwt_identity()

        if 'image' not in file.content_type:
            return {'error' : '이미지 파일만 업로드하세요.'}
        
        # 1-1. 이미 등록된 유저인지 확인한다.
        try:
            connection = get_connection()
            query = '''select *
                    from face
                    where userId = %s;'''
            record = (userId, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)        
            result_list = cursor.fetchall()
            cursor.close()
            connection.close()

            if result_list:
                return {'error': '이미 얼굴정보가 등록된 유저입니다.'}, 400

        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return {'error' : str(e)}, 500
        

        fileName = f'user_{userId}.jpg'
        filePath = 'face/' + fileName

        try:
            # 2. S3에 사진을 업로드한다.
            client = boto3.client('s3',
                                aws_access_key_id= Config.ACCESS_KEY,
                                aws_secret_access_key= Config.SECRET_ACCESS)

            client.upload_fileobj(file,
                                Config.S3_BUCKET,
                                filePath,
                                ExtraArgs = {'ACL':'public-read', 'ContentType':'image/jpg'})

            imgUrl = Config.S3_LOCATION + filePath

            # 3. 사진의 얼굴을 컬렉션에 추가하고 FaceId를 가져온다.
            client = boto3.client('rekognition',
                                'ap-northeast-2',
                                aws_access_key_id= Config.ACCESS_KEY,
                                aws_secret_access_key= Config.SECRET_ACCESS)

            response = client.index_faces(CollectionId=Config.COLLECTION_ID,
                                        Image={'S3Object':{'Bucket':Config.S3_BUCKET,'Name':filePath}},
                                        ExternalImageId=fileName,
                                        MaxFaces=1,
                                        QualityFilter="AUTO",
                                        DetectionAttributes=['DEFAULT'])
            # print(response)
            
            if not response['FaceRecords']:
                return {'error': '사진에서 얼굴 정보를 찾을 수 없습니다.'}, 400

            faceId = response['FaceRecords'][0]['Face']['FaceId']

        except ClientError as e:
            """
            {
                'Error': {
                    'Code': 'SomeServiceException',
                    'Message': 'Details/context around the exception or error'
                },
                'ResponseMetadata': {
                    'RequestId': '1234567890ABCDEF',
                    'HostId': 'host ID data will appear here as a hash',
                    'HTTPStatusCode': 400,
                    'HTTPHeaders': {'header metadata key/values will appear here'},
                    'RetryAttempts': 0
                }
            }
            """
            return {'error' : str(e)}, e.response['ResponseMetadata']['HTTPStatusCode']
       
        # 4. DB에 저장한다.
        try:
            connection = get_connection()
            query = '''insert into 
                    face
                    (userId, imgUrl, faceId)
                    values
                    (%s, %s, %s);'''
            record = (userId, imgUrl, faceId)
            cursor = connection.cursor()
            cursor.execute(query, record)
            connection.commit()

            cursor.close()
            connection.close()

        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return {'error' : str(e)}, 500
        
        return {'result' : 'success',
                'userId' : userId,
                'imgUrl' : imgUrl,
                'faceId' : faceId}, 200
    

    # 컬렉션에 등록된 얼굴 삭제 API
    @jwt_required()
    def delete(self):

        userId = get_jwt_identity()
        
        # 1. userId로 faceId를 가져온다.
        try:
            connection = get_connection()
            query = '''select imgUrl, faceId
                    from face
                    where userId = %s;'''
            record = (userId, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)        
            result_list = cursor.fetchall()

            cursor.close()
            connection.close()

            if not result_list:
                return {'error': '얼굴정보가 등록되지 않은 유저입니다.'}, 400
            
            faceId = result_list[0]['faceId']
            imgUrl = result_list[0]['imgUrl']
      
        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return {'error' : str(e)}, 500

        # 2. 등록된 faceId를 컬렉션에서 삭제한다.
        try:
            client=boto3.client('rekognition',
                                'ap-northeast-2',
                                aws_access_key_id= Config.ACCESS_KEY,
                                aws_secret_access_key= Config.SECRET_ACCESS)

            response=client.delete_faces(CollectionId=Config.COLLECTION_ID,
                                    FaceIds=[faceId])

        except ClientError as e:
            return {'error' : str(e)}, e.response['ResponseMetadata']['HTTPStatusCode']

        # S3에 저장된 이미지도 삭제
        try:
            client = boto3.client('s3',
                                aws_access_key_id= Config.ACCESS_KEY,
                                aws_secret_access_key= Config.SECRET_ACCESS)
            
            objectKey = str(imgUrl.split('/')[3])+'/'+str(imgUrl.split('/')[4])
            client.delete_object(Bucket=Config.S3_BUCKET, Key=objectKey)

        except ClientError as e:
            return {'error' : str(e)}, e.response['ResponseMetadata']['HTTPStatusCode']

        
        # DB에서도 삭제한다.
        try:
            connection = get_connection()
            query = '''delete from
                    face
                    where faceId = %s;'''
            record = (faceId, )
            cursor = connection.cursor()
            cursor.execute(query, record)        
            connection.commit()

            cursor.close()
            connection.close()
        
        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return {'error' : str(e)}, 500
        
        return {'result' : 'success',
                'msg' : f"userId: {userId}'s face information was deleted."}, 200
    

class FaceSearchResource(Resource):

    # 얼굴검색 API
    def post(self):

        # 1. 클라이언트로부터 데이터를 받아온다.
        # form-data
        # -photo : file
        if 'photo' not in request.files:
            return {'error' : '파일을 업로드 하세요.'}, 400
        
        file = request.files['photo']

        # todo: restaurantId를 업체용 앱 jwt에서 받도록 수정
        restaurantId = int(request.args.get('restaurantId'))

        if 'image' not in file.content_type:
            return {'error' : '이미지 파일만 업로드하세요.'}

        # 2. 이미지파일을 base64로 인코딩
        baseImg = base64.b64encode(file.read())
        # 인코딩 된 사진을 byte로 디코딩
        byteImg = base64.decodebytes(baseImg)

        # 3. 컬렉션에서 이미지 검색
        try:
            client=boto3.client('rekognition',
                                'ap-northeast-2',
                                aws_access_key_id= Config.ACCESS_KEY,
                                aws_secret_access_key= Config.SECRET_ACCESS)
            
            threshold = 95
            maxFaces=1

            response=client.search_faces_by_image(CollectionId=Config.COLLECTION_ID,
                                Image= {'Bytes': byteImg},
                                FaceMatchThreshold= threshold,
                                MaxFaces= maxFaces)
            print(response)
            faceMatches=response['FaceMatches']

            if not faceMatches:

                return {'result' : 'success',
                        'msg' : '등록되지 않은 고객입니다.'}, 200

            faceId = faceMatches[0]['Face']['FaceId']
            similarity = faceMatches[0]['Similarity']

        except ClientError as e:
            return {'error' : str(e)}, e.response['ResponseMetadata']['HTTPStatusCode']

        # 4. DB에서 일치하는 회원의 정보, 주문정보 가져오기
  
        try:
            connection = get_connection()
            query = '''
                    select f.userId,f.imgUrl, f.faceId, u.nickname, u.phone,
                        o.id as orderId, o.restaurantId, o.people, o.reservTime,
                        o.type, o.createdAt, o.isFinished
                    from face f
                    join users u
                    on f.userId = u.id
                    left join orders o
                    on f.userId = o.userId and o.restaurantId = %s and o.isFinished = 0
                    where faceId = %s
                    order by reservTime asc;
                    '''
            record = (restaurantId, faceId)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            result_list = cursor.fetchall()
            
            for row in result_list:
                if row['orderId']:
                    row['reservTime'] = row['reservTime'].isoformat()
                    row['createdAt'] = row['createdAt'].isoformat()
            
            cursor.close()
            connection.close()
        
        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return {'error' : str(e)}, 500

        return {'result' : 'success',
                'items' : result_list,
                'similarity' : similarity}, 200
