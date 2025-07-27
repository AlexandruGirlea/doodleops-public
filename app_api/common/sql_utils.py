from core.settings import SessionLocal


def get_db_conn():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
