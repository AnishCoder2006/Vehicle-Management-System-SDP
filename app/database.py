import os
from urllib.parse import urlparse
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or not DATABASE_URL.strip():
    DATABASE_URL = "sqlite:///./vehicle_service.db"

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # If using MySQL, try to auto-create the database if it doesn't exist
    try:
        if "mysql" in DATABASE_URL:
            parsed = urlparse(DATABASE_URL)
            db_name = parsed.path.lstrip("/")
            if db_name:
                server_url = DATABASE_URL.rsplit("/", 1)[0]
                temp_engine = create_engine(server_url)
                with temp_engine.connect() as conn:
                    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}`"))
                    conn.commit()
                temp_engine.dispose()
    except Exception:
        # Fall through to standard engine creation
        pass

    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
