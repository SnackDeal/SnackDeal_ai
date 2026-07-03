# 파이썬 3.13 슬림 버전 사용 (용량 최적화)
FROM python:3.13-slim

WORKDIR /app

# 시스템 패키지 업데이트 및 빌드 필수 패키지 설치 후 캐시 삭제 (용량 확보)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 요구사항 파일 복사 및 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 전체 복사
COPY . .

# FastAPI 같은 프레임워크를 쓴다면 보통 8000번 포트를 씁니다
EXPOSE 8000

# 서버 실행 (uvicorn 예시)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
