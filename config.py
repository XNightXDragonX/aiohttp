import os
from dotenv import load_dotenv


load_dotenv()


class Config:
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:123@localhost:5432/new_ads_db')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'My_JWT_Key')
    JWT_ALGORITHM = 'HS256'