from flask import request
from flask_restful import Resource
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from mysql.connector import Error

from config import Config
from mysql_connection import get_connection


class CollectionResource(Resource):

    # 컬렉션 생성 API
    def post(self):

        collectionId = request.args.get('collectionId')
 
        client = boto3.client('rekognition',
                                'ap-northeast-2',
                                aws_access_key_id= Config.ACCESS_KEY,
                                aws_secret_access_key= Config.SECRET_ACCESS)

        try:
            response=client.create_collection(CollectionId=collectionId)       

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
            return {'Code': e.response['Error']['Code'],
                    'Message': e.response['Error']['Message']}, e.response['ResponseMetadata']['HTTPStatusCode']
        
        return {'result' : 'success',
                'Collection Arn' : response['CollectionArn']}, 200


    # 컬렉션 정보 조회 API
    def get(self):

        collectionId = request.args.get('collectionId')

        client = boto3.client('rekognition',
                                'ap-northeast-2',
                                aws_access_key_id= Config.ACCESS_KEY,
                                aws_secret_access_key= Config.SECRET_ACCESS)

        try:
            response=client.describe_collection(CollectionId=collectionId)
            # print("Collection Arn: "  + response['CollectionARN'])
            # print("Face Count: "  + str(response['FaceCount']))
            # print("Face Model Version: "  + response['FaceModelVersion'])
            # print("Timestamp: "  + str(response['CreationTimestamp']))

            
        except ClientError as e:
            return {'Code': e.response['Error']['Code'],
                    'Message': e.response['Error']['Message']}, e.response['ResponseMetadata']['HTTPStatusCode']
        
        return {'result': 'success',
                "CollectionARN": response['CollectionARN'],
                "CreationTimestamp": response['CreationTimestamp'].isoformat(),
                "FaceCount": response['FaceCount'],
                "FaceModelVersion": response['FaceModelVersion']}, 200

    
    # 컬렉션 삭제
    def delete(self):
        
        collectionId = request.args.get('collectionId')

        print('Attempting to delete collection ' + collectionId)
        client = boto3.client('rekognition',
                                'ap-northeast-2',
                                aws_access_key_id= Config.ACCESS_KEY,
                                aws_secret_access_key= Config.SECRET_ACCESS)
        try:
            response=client.delete_collection(CollectionId=collectionId)
            status_code=response['StatusCode']
            
        except ClientError as e:
            return {'Code': e.response['Error']['Code'],
                    'Message': e.response['Error']['Message']}, e.response['ResponseMetadata']['HTTPStatusCode']
       
        return {'result' : 'success',
                'msg': f'collection id: {collectionId} was deleted.'}, status_code


        
class CollectionListResource(Resource):

    # 생성한 컬렉션 리스트 확인
    def get(self):

        maxResult = 20
        client = boto3.client('rekognition',
                                'ap-northeast-2',
                                aws_access_key_id= Config.ACCESS_KEY,
                                aws_secret_access_key= Config.SECRET_ACCESS)

        try:
            collection_count=0
            done=False
            collectionList = []
            response=client.list_collections(MaxResults=maxResult)
                       
            while done==False:
                collections=response['CollectionIds']

                for collection in collections:
                    print(collection)
                    collectionList.append(collection)
                    collection_count+=1
                if 'NextToken' in response:
                    nextToken=response['NextToken']
                    response=client.list_collections(NextToken=nextToken,MaxResults=maxResult)
                    
                else:
                    done=True

        except ClientError as e:
            return {'Code': e.response['Error']['Code'],
                    'Message': e.response['Error']['Message']}, e.response['ResponseMetadata']['HTTPStatusCode']

        return {'result' : 'success',
                'collectionList' : collectionList,
                'collectionCount' : collection_count}, 200
