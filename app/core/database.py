from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. DB 파일 위치 설정 (프로젝트 폴더에 waste.db 라는 파일로 생성됨)
SQLALCHEMY_DATABASE_URL = "sqlite:///./waste.db"

# 2. 엔진 생성 (SQLite 설정)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. 세션 생성 (DB와 대화하는 통로)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. 모델의 기본 클래스
Base = declarative_base()

# 5. DB 세션을 가져오는 함수 (나중에 API에서 사용함)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()