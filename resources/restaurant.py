from flask import request
from flask_restful import Resource
from mysql.connector import Error
from flask_jwt_extended import jwt_required, get_jwt_identity
import pandas as pd
import numpy as np
from haversine import haversine

from mysql_connection import get_connection


class RestaurantListResource(Resource):

    # 식당리스트 조회 API
    @jwt_required(optional=True)
    def get(self):

        userId = get_jwt_identity()

        # 클라이언트에서 쿼리스트링으로 보내는 데이터는
        # request.args에 들어있다.
        lat = request.args.get('lat')
        lng = request.args.get('lng')
        offset = request.args.get('offset')
        limit = request.args.get('limit')
        order = request.args.get('order')
        keyword = request.args.get('keyword')
        
        if not lat or not lng:
            return {'error' : 'lat와 lng는 필수 파라미터입니다.'}, 400

        # 기본값
        if not offset:
            offset = 0
        
        if not limit:
            limit = 20

        if not order:
            order = 'distance'

        if not keyword:
            keyword = ''

        lat = float(lat)
        lng = float(lng)
        offset = int(offset)
        limit = int(limit)

        if not (-90 <= lat <=90):
            return {'error' : 'lat값을 확인하세요.'}, 400
        
        if not (-180 <= lng <=180):
            return {'error' : 'lng값을 확인하세요.'}, 400
        
        # 여백 처리
        keyword = keyword.strip()

        # 검색어가 없는 경우: 전체 검색
        if not keyword:
            try:
                connection = get_connection()
                query = '''
                        select r.id, r.name, r.category, r.locCity, r.locDistrict, r.locDetail,
                            r.longitude, r.latitude, r.imgUrl,
                            ifnull(count(rv.restaurantId), 0) as count,
                            ifnull(avg(rv.rating), 0) as rating
                        from restaurant r
                        left join review rv
                        on r.id = rv.restaurantId
                        group by r.id;
                        '''  
                cursor = connection.cursor(dictionary=True)
                cursor.execute(query)
                result_list = cursor.fetchall()

                for row in result_list:
                    row['rating'] = float(row['rating'])

                cursor.close()
                connection.close()
            
            except Error as e:
                print(e)
                cursor.close()
                connection.close()
                return {'error' : str(e)}, 500
            
        # 검색어가 있는 경우
        else:
            # 띄어쓰기로 분리
            # ex) '인천 서구 한식' -> '+인천*+서구*+한식*'
            keywordList = keyword.split(' ')
            search = ''
            for word in keywordList:
                search = search + f'+{word}*'

            try:
                connection = get_connection()
                query = '''
                        select r.id, r.name, r.category, r.locCity, r.locDistrict, r.locDetail,
                            r.longitude, r.latitude, r.imgUrl,
                            ifnull(count(rv.restaurantId), 0) as count,
                            ifnull(avg(rv.rating), 0) as rating
                        from restaurant r
                        left join review rv
                        on r.id = rv.restaurantId
                        where match(locCity, locDistrict, locDetail, name, category)
                        against("%s" in boolean mode)
                        group by r.id;
                        '''  
                cursor = connection.cursor(dictionary=True)
                record = (search,)
                cursor.execute(query, record)
                result_list = cursor.fetchall()

                for row in result_list:
                    row['rating'] = float(row['rating'])

                cursor.close()
                connection.close()
            
            except Error as e:
                print(e)
                cursor.close()
                connection.close()
                return {'error' : str(e)}, 500
            
            if not result_list:
                return {'msg' : '검색결과가 없습니다.'}, 205 


        # 가게와의 거리를 계산하기 위해 데이터프레임으로
        df = pd.DataFrame(data=result_list)

        # print(df)
        myLocation = (lat, lng)
        # print(myLocation)

        LocationList = np.array(df[['latitude','longitude']])

        # 하버사인 거리 계산
        distanceList = []
        for row in LocationList:
            distance = round(haversine(myLocation, row, unit='m'))
            distanceList.append(distance)
        
        # 거리 컬럼 추가
        df['distance'] = distanceList
        
        # 가까운 순 정렬
        if order == 'distance':
            df = df.sort_values(order, ascending=True)
        # 리뷰갯수 or 평점 순 정렬
        elif order == 'count' or order == 'rating':
            df = df.sort_values(order, ascending=False)
        else:
            return {'error' : '올바르지 않은 order 입니다.'}, 400
        
        # print(df)
        result_list = df.iloc[offset:limit]
        result_list = result_list.to_dict('records')
        # print(result_list)

        return {'result' : 'success',
                'items' : result_list,
                'count' : len(result_list),
                'msg' : 'hi'}
    

class RestaurantResource(Resource):

    # 식당 상세정보 조회 API
    @jwt_required(optional=True) 
    def get(self, restaurantId):
        
        try:
            connection = get_connection()
            query = '''
                    select r.*, 
                        ifnull(count(rv.restaurantId), 0) as cnt,
                        ifnull(avg(rv.rating), 0) as avg 
                    from restaurant r
                    left join review rv
                    on r.id = rv.restaurantId
                    where r.id = %s;
                    '''  
            record = (restaurantId, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            result = cursor.fetchone()

            cursor.close()
            connection.close()

            # safe coding
            if result['id'] is None:
                return {'errer' : '잘못된 restaurantId 입니다.'}, 400

            result['createdAt'] = result['createdAt'].isoformat()
            result['updatedAt'] = result['updatedAt'].isoformat()
            result['avg'] = float(result['avg'])
            # print(result)

        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return {'error' : str(e)}, 500
        
        return {'result' : 'success',
                'restaurantInfo' : result}, 200
    

class RestaurantMenuResource(Resource):

    # 식당 메뉴리스트 조회 API
    @jwt_required(optional=True) 
    def get(self, restaurantId):

        offset = request.args.get('offset')
        limit = request.args.get('limit')

        # 기본값
        if not offset:
            offset = 0
        if not limit:
            limit = 20

        try:
            connection = get_connection()
            query = '''
                    select * 
                    from menu
                    where restaurantId = %s
                    limit '''+offset+''', '''+limit+''';
                    '''  
            record = (restaurantId, )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, record)
            result_list = cursor.fetchall()

            for row in result_list:
                row['createdAt'] = row['createdAt'].isoformat()
                row['updatedAt'] = row['updatedAt'].isoformat()
            
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


class RestaurantOrderResource(Resource):
    
    # 식당 주문 API
    @jwt_required()
    def post(self, restaurantId):

        userId = get_jwt_identity()
        data = request.get_json()
        menuInfo = data['menuInfo']

        try:
            connection = get_connection()
            # 1. order 테이블에 저장
            query = '''
                    insert into orders
                    (userId, restaurantId, people, reservTime)
                    values (%s, %s, %s, %s);
                    '''
            record = [userId, restaurantId, data['people'], data['reservTime']]

            cursor = connection.cursor()
            cursor.execute(query, record)

            orderId = cursor.lastrowid

            # 2. orderDetail 테이블에 메뉴 저장
            for row in menuInfo:
                query = '''
                        insert into orderDetail
                        (orderId, menuId, count)
                        values (%s, %s, %s);
                        '''
                record = [orderId, row['menuId'], row['count']]
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
                'orderId' : orderId}, 200