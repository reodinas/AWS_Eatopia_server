from flask import request
from flask_restful import Resource
from mysql.connector import Error
from flask_jwt_extended import jwt_required, get_jwt_identity
import pandas as pd
import numpy as np
from haversine import haversine

from mysql_connection import get_connection


class OrderListResource(Resource):

    # 내 주문내역 조회 API
    @jwt_required()
    def get(self):

        userId = get_jwt_identity()
        offset = request.args.get('offset')
        limit = request.args.get('limit')

         # 기본값
        if not offset:
            offset = 0
        if not limit:
            limit = 20

        try:
            connection = get_connection()
            # 주문한 시간이 늦은 순으로 정렬
            query = '''
                    select *
                    from orders
                    where userId = %s
                    order by createdAt desc;
                    limit '''+offset+''', ''' +limit+'''
                    '''
            record = (userId, )

            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            result_list = cursor.fetchall()

            for row in result_list:
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
                'count' : len(result_list)}, 200



class OrderResource(Resource):

    # 주문상세정보 조회 API
    @jwt_required()
    def get(self, orderId):
        
        userId = get_jwt_identity()

        try:
            connection = get_connection()
            query = '''
                    select *
                    from orders
                    where id = %s;
                    '''
            record = (orderId, )
            
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            result = cursor.fetchone()

            result['reservTime'] = result['reservTime'].isoformat()
            result['createdAt'] = result['createdAt'].isoformat()

            # 요청한 유저아이디가 주문정보의 유저아이디와 다를 경우
            if userId != int(result['userId']):
                cursor.close()
                connection.close()
                return {'error' : '접근 권한이 없습니다.'}, 401
            
            # 메뉴정보
            query = '''
                    select od.menuId, od.count, m.menuName, 
                        m.price, m.description, m.imgUrl
                    from orderDetail od
                    join menu m
                    on od.menuId = m.id
                    where orderId = %s;
                    '''
            record = (orderId, )
            cursor.execute(query, record)
            menuInfo = cursor.fetchall()

            result['menuInfo'] = menuInfo

            cursor.close()
            connection.close()


        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return {'error' : str(e)}, 500

        return {'result' : 'success',
                'orderInfo' : result}, 200