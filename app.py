from flask import Flask
from flask_restful import Api
from flask_jwt_extended import JWTManager

from config import Config
from resources.collection import CollectionListResource, CollectionResource
from resources.face import FaceResource, FaceSearchResource
from resources.order import OrderResource, OrderListResource
from resources.restaurant import RestaurantMenuResource, RestaurantResource, RestaurantListResource, RestaurantOrderResource

from resources.user import UserLoginResource, UserLogoutResource, UserRegisterResource, UserResource
from resources.user import jwt_blocklist

app = Flask(__name__)
# 환경변수 셋팅
app.config.from_object(Config)

# JWT 매니저 초기화(initialize)
# JWTManager(app)을 설정해줘야 flask istance에서 jwt를 사용할 수 있게 된다.
jwt = JWTManager(app)

# 로그아웃된 토큰으로 요청하는 경우 처리하는 코드작성.
@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    return jti in jwt_blocklist


api = Api(app)

# 경로와 리소스를 연결한다.
api.add_resource(UserRegisterResource, '/user/register')
api.add_resource(UserLoginResource, '/user/login')
api.add_resource(UserLogoutResource, '/user/logout')
api.add_resource(UserResource, '/user')

api.add_resource(RestaurantListResource, '/restaurant')
api.add_resource(RestaurantResource, '/restaurant/<int:restaurantId>')
api.add_resource(RestaurantMenuResource, '/restaurant/<int:restaurantId>/menu')
api.add_resource(RestaurantOrderResource, '/restaurant/<int:restaurantId>/order')

api.add_resource(OrderListResource, '/order')
api.add_resource(OrderResource, '/order/<int:orderId>')

api.add_resource(CollectionResource, '/collection')
api.add_resource(CollectionListResource, '/collection/list')
api.add_resource(FaceResource, '/faces')
api.add_resource(FaceSearchResource, '/faces/search')



if __name__ == '__main__':
    app.run()
    