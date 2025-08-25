import json
import asyncio
from aiohttp import web
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from config import Config
from extensions import create_access_token, check_db_connection, engine, AsyncSessionLocal, Base, decode_token
from models import User, Ad
from middleware import jwt_middleware


async def init_db():
    try:
        await asyncio.sleep(2)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ База данных создана успешно!")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        raise


async def health_check(request):
    try:
        db_connected = await check_db_connection()
        return web.json_response({
            'status': 'healthy',
            'database': 'connected' if db_connected else 'no connection'
        })
    except Exception as e:
        return web.json_response({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)


async def register(request):
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({'error': 'Неверный JSON'}, status=400)
    
    if not all(i in data for i in ['email', 'password']):
        return web.json_response({'error': 'Заполните все поля!'}, status=400)
    
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(User).where(User.email == data['email']))
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                return web.json_response({'error': 'Пользователь с таким email уже существует!'}, status=400)
            
            user = User(email=data['email'])
            user.set_password(data['password'])
            session.add(user)
            await session.commit()
            
            return web.json_response({'message': 'Пользователь успешно зарегистрирован!'}, status=201)
            
        except IntegrityError:
            await session.rollback()
            return web.json_response({'error': 'Ошибка при создании пользователя'}, status=400)
        except Exception as e:
            await session.rollback()
            return web.json_response({'error': 'Внутренняя ошибка сервера'}, status=500)


async def login(request):
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({'error': 'Неверный JSON'}, status=400)
    
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(User).where(User.email == data['email']))
            user = result.scalar_one_or_none()
            
            if not user or not user.check_password(data['password']):
                return web.json_response({'error': 'Данные неверны'}, status=401)
            
            access_token = create_access_token(identity=str(user.id))
            return web.json_response({'access_token': access_token}, status=200)
        except Exception as e:
            return web.json_response({'error': 'Внутренняя ошибка сервера'}, status=500)


async def create_ad(request):
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({'error': 'Неверный JSON'}, status=400)
    
    if not all(i in data for i in ['title', 'description']):
        return web.json_response({'error': 'Заполните все поля!'}, status=400)
    
    user_id = request['user_id']
    
    async with AsyncSessionLocal() as session:
        try:
            ad = Ad(
                title=data['title'],
                description=data['description'],
                owner_id=int(user_id)
            )
            
            session.add(ad)
            await session.commit()
            await session.refresh(ad)
            
            return web.json_response(ad.to_dict(), status=201)
        except Exception as e:
            await session.rollback()
            return web.json_response({'error': 'Ошибка при создании объявления'}, status=500)


async def update_ad(request):
    try:
        ad_id = int(request.match_info['ad_id'])
    except ValueError:
        return web.json_response({'error': 'Неверный ID объявления'}, status=400)
    
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({'error': 'Неверный JSON'}, status=400)
    
    user_id = request['user_id']
    
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(Ad).where(Ad.id == ad_id))
            ad = result.scalar_one_or_none()
            
            if not ad:
                return web.json_response({'error': 'Объявление не найдено'}, status=404)
            
            if int(user_id) != ad.owner_id:
                return web.json_response({'error': 'Нельзя редактировать чужое объявление'}, status=403)
            
            if 'title' in data:
                ad.title = data['title']
            if 'description' in data:
                ad.description = data['description']
            
            await session.commit()
            await session.refresh(ad)
            
            return web.json_response(ad.to_dict())
        except Exception as e:
            await session.rollback()
            return web.json_response({'error': 'Внутренняя ошибка сервера'}, status=500)


async def get_ads(request):
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(Ad))
            ads = result.scalars().all()
            
            return web.json_response([ad.to_dict() for ad in ads])
        except Exception as e:
            return web.json_response({'error': 'Внутренняя ошибка сервера'}, status=500)


async def get_ad(request):
    try:
        ad_id = int(request.match_info['ad_id'])
    except ValueError:
        return web.json_response({'error': 'Неверный ID объявления'}, status=400)
    
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(Ad).where(Ad.id == ad_id))
            ad = result.scalar_one_or_none()
            
            if not ad:
                return web.json_response({'error': 'Объявление не найдено'}, status=404)
            
            return web.json_response(ad.to_dict())
        except Exception as e:
            return web.json_response({'error': 'Внутренняя ошибка сервера'}, status=500)


async def delete_ad(request):
    try:
        ad_id = int(request.match_info['ad_id'])
    except ValueError:
        return web.json_response({'error': 'Неверный ID объявления'}, status=400)
    
    user_id = request['user_id']
    
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(Ad).where(Ad.id == ad_id))
            ad = result.scalar_one_or_none()
            
            if not ad:
                return web.json_response({'error': 'Объявление не найдено'}, status=404)
            
            if int(user_id) != ad.owner_id:
                return web.json_response({'error': 'Нельзя удалить чужое объявление'}, status=403)
            
            await session.delete(ad)
            await session.commit()
            
            return web.json_response({'message': 'Объявление удалено!'}, status=200)
        except Exception as e:
            await session.rollback()
            return web.json_response({'error': 'Внутренняя ошибка сервера'}, status=500)


app = web.Application(middlewares=[jwt_middleware])

# Маршруты
app.router.add_get('/health', health_check)
app.router.add_post('/register', register)
app.router.add_post('/login', login)
app.router.add_post('/ads', create_ad)
app.router.add_put(r'/ads/{ad_id:\d+}', update_ad)  # ИСПРАВЛЕНО
app.router.add_get('/ads', get_ads)  # ДОБАВЛЕНО
app.router.add_get(r'/ads/{ad_id:\d+}', get_ad)
app.router.add_delete(r'/ads/{ad_id:\d+}', delete_ad)


async def on_startup(app):
    print("🚀 Запуск приложения...")
    try:
        await init_db()
        print("✅ Приложение успешно запущено!")
    except Exception as e:
        print(f"❌ Ошибка при запуске: {e}")
        raise


async def on_cleanup(app):
    print("🛑 Остановка приложения...")
    await engine.dispose()


if __name__ == '__main__':
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    web.run_app(app, host='0.0.0.0', port=8000)