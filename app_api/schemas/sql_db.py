from sqlalchemy import Column, Integer, String, DateTime, Text

from core.settings import DB_Base


class AuthUser(DB_Base):
    __tablename__ = "app_users_customuser"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(150), unique=True, nullable=False)


class DjangoSession(DB_Base):
    __tablename__ = "django_session"

    session_key = Column(
        String(40), primary_key=True, index=True, autoincrement=True
    )
    session_data = Column(Text, nullable=False)
    expire_date = Column(DateTime, nullable=False)
