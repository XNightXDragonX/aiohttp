from aiohttp import web
from extensions import decode_token


@web.middleware
async def jwt_middleware(request, handler):
    if request.path in ['/register', '/login', '/health']:
        return await handler(request)    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return web.json_response(
            {'error': 'Требуется авторизация'}, 
            status=401
        )
    token = auth_header.split(' ')[1]
    payload = decode_token(token)
    if not payload:
        return web.json_response(
            {'error': 'Неверный токен'}, 
            status=401
        )
    request['user_id'] = payload['identity']
    return await handler(request)