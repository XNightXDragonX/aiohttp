import jwt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from config import Config


engine = create_async_engine(
    Config.DATABASE_URL,
    echo=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800
)


AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


def create_access_token(identity: str) -> str:
    return jwt.encode(
        {'identity': identity},
        Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM
    )
    
    
def decode_token(token: str):
    try:
        payload = jwt.decode(
            token,
            Config.JWT_SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM]
        )
        return payload
    except jwt.InvalidTokenError:
        return None
    
    
async def check_db_connection():
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT 1'))
        return result.scalar() == 1