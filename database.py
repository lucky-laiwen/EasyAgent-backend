from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 配置数据库
SQLALCHEMY_DATABASE_URL = 'mysql+mysqlconnector://root:08180924@localhost:3306/easyagent'
# 创建数据库引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,
    pool_pre_ping=True
)
# Session工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基类
Base = declarative_base()

# 创建数据库表
Base.metadata.create_all(bind=engine)


# 依赖注入Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
