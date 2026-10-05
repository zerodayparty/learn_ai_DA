import csv  # 이미지 다운로드 목록을 읽는 기본 도구를 가져온다.
import json  # 다운로드 결과를 기록하는 도구를 가져온다.
import shutil  # Kaggle 명령이 설치되어 있는지 확인하는 도구를 가져온다.
import subprocess  # 공식 Kaggle 명령을 실행하는 도구를 가져온다.
from pathlib import Path  # 원본과 표본의 경로를 다루는 도구를 가져온다.


def has_jpeg_markers(path):  # 다운로드된 파일의 기본 JPEG 표시를 확인한다.
    if not path.is_file() or path.stat().st_size < 4:  # 파일이 없거나 비어 있는지 확인한다.
        return False  # 정상 파일로 세지 않는다.
    with path.open('rb') as stream:  # 이미지 파일을 바이트로 읽는다.
        start = stream.read(2)  # JPEG의 시작 표시를 읽는다.
        stream.seek(-2, 2)  # 파일 끝의 두 바이트 위치로 이동한다.
        return start == b'\xff\xd8' and stream.read(2) == b'\xff\xd9'  # JPEG 시작과 종료 표시가 있는지 확인한다.


def download(root, limit=100):  # 최대 100개의 선택 이미지를 준비하는 함수를 정의한다.
    command = shutil.which('kaggle')  # 공식 명령을 실행할 수 있는지 확인한다.
    if command is None:  # 도구가 설치되지 않았는지 확인한다.
        raise SystemExit('먼저 uv tool install kaggle과 kaggle auth login을 실행해.')  # 설치와 로그인 방법만 알린다.
    sample = root / 'data' / 'sample'  # 이미 만들어진 표본 목록 위치를 지정한다.
    raw = root / 'data' / 'raw'  # 원본 이미지 저장 위치를 지정한다.
    with (sample / 'image_manifest.csv').open(newline='', encoding='utf-8') as stream:  # 선택 상품의 다운로드 목록만 읽는다.
        candidates = list(csv.DictReader(stream))  # 제한된 후보 목록을 모은다.
    success, failed, consecutive = [], [], 0  # 성공·실패·연속 실패 수를 기록한다.
    for item in candidates:  # 목록에 있는 파일만 차례로 처리한다.
        value = item['article_id']  # 후보 상품 번호를 읽는다.
        expected = f'images/{value[:3]}/{value}.jpg'  # 허용할 파일 경로를 직접 만든다.
        if not value.isdigit() or len(value) != 10 or item['file_path'] != expected:  # 예상치 못한 경로나 상품 번호를 검사한다.
            raise ValueError('다운로드 목록의 상품 번호 또는 경로가 올바르지 않다.')  # 목록 밖 파일을 받지 않도록 중단한다.
        target = raw / expected  # 저장할 실제 원본 이미지 위치를 지정한다.
        if not has_jpeg_markers(target):  # 이미 받은 정상 파일이면 다운로드를 건너뛴다.
            if target.exists():  # 기존 파일이 있지만 기본 JPEG 검사에 실패했는지 확인한다.
                raise ValueError('기존 이미지가 기본 검사에 실패했다. 파일을 확인한 뒤 다시 실행해.')  # 사용자의 파일을 임의로 덮어쓰지 않는다.
            try:  # 느린 다운로드가 전체 작업을 끝없이 기다리게 하지 않도록 준비한다.
                result = subprocess.run([command, 'competitions', 'download', 'h-and-m-personalized-fashion-recommendations', '-f', expected, '-p', str(raw)], capture_output=True, text=True, timeout=120)  # 전체 다운로드 옵션 없이 한 파일만 공식 도구로 받는다.
                accepted = result.returncode == 0 and has_jpeg_markers(target)  # 요청 성공과 파일의 기본 형식을 함께 확인한다.
            except subprocess.TimeoutExpired:  # 한 파일이 120초 안에 완료되지 않았는지 확인한다.
                accepted = False  # 시간 초과도 실패로 기록하고 다음 후보를 확인한다.
            if not accepted:  # 파일을 성공 목록에 넣을 수 있는지 확인한다.
                failed.append(expected)  # 실패한 파일 경로만 기록한다.
                consecutive += 1  # 연속 실패 수를 늘린다.
                print(f'현재 실패 {len(failed)}개, 다음 후보 확인', flush=True)  # 인증 정보가 섞일 수 있는 원본 오류 출력은 보여 주지 않는다.
                if consecutive >= 5:  # 인증이나 권한 문제로 계속 실패하는지 확인한다.
                    break  # 반복 요청을 멈추고 로그인 상태를 확인하게 한다.
                continue  # 이미지가 없으면 다음 보충 후보로 넘어간다.
        success.append(expected)  # 기본 검사를 통과한 파일만 성공 목록에 넣는다.
        consecutive = 0  # 연속 실패 수를 초기화한다.
        print(f'이미지 준비 {len(success)}/{limit}', flush=True)  # 제한된 다운로드 진행 상태를 알린다.
        if len(success) >= limit:  # 목표 개수를 확보했는지 확인한다.
            break  # 보충 후보를 모두 다운로드하지 않고 멈춘다.
    report = {'target': limit, 'ready': len(success), 'files': success, 'failed': failed, 'validation': 'JPEG start/end markers only; decoding is still required'}  # 완전한 이미지 해석 검증과 구분해서 결과를 기록한다.
    (sample / 'image_download_summary.json').write_text(json.dumps(report, indent=4) + '\n')  # 키나 토큰 없이 결과를 저장한다.
    if len(success) < limit:  # 목표 개수까지 준비하지 못했는지 확인한다.
        raise SystemExit('100장 미만으로 종료했다. 로그인·규칙 동의·다운로드 권한과 결과 기록을 확인해.')  # 완료라고 잘못 알리지 않고 중단 이유를 안내한다.
    print('100장 준비 완료. 모든 픽셀의 정상 여부는 분석 단계에서 확인해야 한다.', flush=True)  # 다운로드와 완전한 이미지 검증을 구분한다.


if __name__ == '__main__':  # 사용자가 직접 실행했을 때만 네트워크 다운로드를 시작한다.
    download(Path(__file__).resolve().parents[1])  # 프로젝트의 표본 목록을 기준으로 이미지를 준비한다.
