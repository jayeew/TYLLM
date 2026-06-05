from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.config import settings


engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """为一次 FastAPI 请求提供数据库会话，并在请求结束后关闭。"""
    db = SessionLocal()
    try:
        # yield 之前是请求进入时的准备，yield 之后由 FastAPI 在响应后继续执行清理。
        yield db
    finally:
        db.close()
