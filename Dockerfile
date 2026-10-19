# Python 3.11이 들어 있는 작은 공식 이미지를 출발점으로 사용한다.
FROM python:3.11-slim
# 공식 uv 이미지에서 이 프로젝트와 같은 버전의 실행 파일만 가져온다.
COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /bin/
# 컨테이너 안에서 프로그램을 실행할 위치를 정한다.
WORKDIR /app
# 화면 없는 실행과 임시 Matplotlib 캐시 위치를 정한다.
ENV MPLBACKEND=Agg MPLCONFIGDIR=/tmp/matplotlib UV_LINK_MODE=copy
# 환경 재현에 필요한 설정만 먼저 복사한다.
COPY pyproject.toml uv.lock README.md ./
# 노트북 편집 도구 없이 잠금 파일의 분석용 라이브러리만 설치한다.
RUN uv sync --locked --no-dev
# 분석 소스만 복사하고 데이터나 인증 파일은 이미지에 넣지 않는다.
COPY src ./src
# 터미널 분석의 시작 파일을 복사한다.
COPY main.py ./
# 이미 설치된 환경으로 실행해 실행 시 의존성을 다시 받지 않는다.
CMD ["/app/.venv/bin/python", "main.py"]
