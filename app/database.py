# 文件: app/database.py (最终修正完整版)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os
from dotenv import load_dotenv

# 1. 确保在程序早期加载 .env 文件中的环境变量
load_dotenv()

# 2. 从环境变量中读取 DATABASE_URL
#    os.getenv() 会返回 .env 文件中定义的值，或者 None (如果未定义)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 3. 添加一个健壮性检查，确保 DATABASE_URL 已经被正确设置
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("关键错误: 数据库连接URL未在 .env 文件中设置！")

# 4. 根据 DATABASE_URL 的内容，决定是否添加额外的连接参数
connect_args = {}
# "check_same_thread": False 这个参数只在连接 SQLite 时才需要
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# 5. 使用加载到的 URL 创建 SQLAlchemy 引擎
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

# 后续部分保持不变
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()