import csv  # 이미지 다운로드 목록을 읽는 기본 도구를 가져온다.
import json  # 다운로드 결과를 기록하는 도구를 가져온다.
import shutil  # Kaggle 명령이 설치되어 있는지 확인하는 도구를 가져온다.
import subprocess  # 공식 Kaggle 명령을 실행하는 도구를 가져온다.
from pathlib import Path  # 원본과 표본의 경로를 다루는 도구를 가져온다.
from tempfile import TemporaryDirectory  # 다운로드 파일을 검사할 임시 폴더 도구를 가져온다.


FAILURE_MESSAGES = {  # 원본 오류 대신 출력할 안전한 설명을 정한다.
    'authentication': '계정 인증 실패, Kaggle 로그인을 확인해',  # 인증 오류만 구분한다.
    'permission': '접근 거부, 대회 규칙과 계정 권한을 확인해',  # 권한 오류만 구분한다.
    'not_found': '서버에서 해당 이미지 파일을 찾지 못함',  # 없는 이미지 후보를 구분한다.
    'rate_limit': '요청 제한, 잠시 후 다시 실행해',  # 과도한 요청 제한을 구분한다.
    'network': '서버 연결 또는 네트워크 오류',  # 연결 오류만 구분한다.
    'timeout': '한 파일 다운로드가 120초를 초과함',  # 시간 초과를 구분한다.
    'missing_file': '명령은 성공했지만 받은 이미지 파일을 찾지 못함',  # 저장 경로 문제를 구분한다.
    'invalid_jpeg': '받은 파일이 기본 JPEG 검사에 실패함',  # 파일 형식 문제를 구분한다.
    'cli_error': 'Kaggle 명령 실행 실패, 설치 버전과 도움말을 확인해',  # 분류하지 못한 오류를 안전하게 알린다.
}  # 고정 설명에는 토큰이나 원본 오류 출력을 넣지 않는다.


def failure_reason(result):  # Kaggle 오류를 비밀 정보 없는 분류로 바꾼다.
    output = ((getattr(result, 'stderr', '') or '') + '\n' + (getattr(result, 'stdout', '') or '')).lower()  # 원본 출력은 메모리 안에서만 확인한다.
    for markers, reason in [  # 알려진 오류 표현을 정해진 분류와 연결한다.
        (('401', 'unauthorized', 'unauthenticated'), 'authentication'),  # 인증 문제의 대표 표현이다.
        (('403', 'forbidden', 'permission denied'), 'permission'),  # 권한 문제의 대표 표현이다.
        (('404', 'not found'), 'not_found'),  # 서버에 파일이 없는 경우다.
        (('429', 'too many requests'), 'rate_limit'),  # 서버 요청 제한인 경우다.
        (('connection', 'name resolution', 'network', '503', '502', '504'), 'network'),  # 서버나 네트워크 연결 문제다.
    ]:  # 어떤 분류에도 맞지 않으면 일반 오류로 처리한다.
        if any(marker in output for marker in markers):  # 알려진 표현이 있는지 확인한다.
            return reason  # 원문 대신 안전한 분류만 반환한다.
    return 'cli_error'  # 알 수 없는 오류를 로그인 실패로 단정하지 않는다.


def copy_image(source, target):  # 확인한 이미지를 정해진 폴더로 복사한다.
    target.parent.mkdir(parents=True, exist_ok=True)  # 상품 번호 앞 세 자리 폴더까지 만든다.
    with source.open('rb') as incoming, target.open('xb') as outgoing:  # 기존 대상 파일을 덮어쓰지 않고 새 파일만 만든다.
        shutil.copyfileobj(incoming, outgoing)  # 원본 파일 내용은 바꾸지 않고 복사한다.


def fetch_image(command, raw, expected):  # Kaggle 버전별 저장 위치 차이를 처리한다.
    target = raw / expected  # 프로젝트에서 사용할 최종 이미지 위치를 정한다.
    legacy = raw / target.name  # 이전 코드가 raw 바로 아래에 받은 파일을 찾는다.
    if has_jpeg_markers(legacy):  # 이미 받은 정상 파일이 있는지 확인한다.
        copy_image(legacy, target)  # 재다운로드 없이 올바른 경로에 복사하고 기존 파일도 보존한다.
        return None  # 파일이 준비됐으므로 실패 이유가 없다.
    raw.mkdir(parents=True, exist_ok=True)  # 임시 다운로드를 담을 원본 폴더를 준비한다.
    with TemporaryDirectory(prefix='.hm-download-', dir=raw) as folder:  # 이번 요청만 담는 임시 폴더를 만든다.
        staging = Path(folder)  # 임시 다운로드 위치를 경로로 다룬다.
        try:  # 한 파일 요청의 제한 시간을 적용한다.
            # 🔥🔥🔥🔥🔥 명령어 부분
            result = subprocess.run([command, 'competitions', 'download', 'h-and-m-personalized-fashion-recommendations', '-f', expected, '-p', str(staging)], capture_output=True, text=True, timeout=120)  # 파일 한 개를 임시 폴더에 요청한다.
        except subprocess.TimeoutExpired:  # 요청이 제한 시간을 넘겼는지 확인한다.
            return 'timeout'  # 원본 오류 출력 없이 시간 초과만 알린다.
        if result.returncode != 0:  # 실제 Kaggle 명령이 실패했는지 확인한다.
            return failure_reason(result)  # 고정된 안전한 오류 분류를 반환한다.
        downloaded = next((path for path in [staging / expected, staging / target.name] if path.is_file()), None)  # 하위 경로 보존 방식과 파일명만 저장하는 방식을 모두 확인한다.
        if downloaded is None:  # 명령은 성공했지만 파일을 못 찾았는지 확인한다.
            return 'missing_file'  # 인증 문제와 저장 경로 문제를 구분한다.
        if not has_jpeg_markers(downloaded):  # 받은 파일의 기본 JPEG 표시를 확인한다.
            return 'invalid_jpeg'  # 잘못된 파일을 최종 이미지로 저장하지 않는다.
        copy_image(downloaded, target)  # 기본 검사를 통과한 파일만 올바른 폴더에 보관한다.
    return None  # 임시 파일 정리 후 성공을 알린다.


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
    failure_details = []  # 원문 오류 대신 파일별 안전한 실패 분류를 기록한다.

    for item in candidates:  # 목록에 있는 파일만 차례로 처리한다.
        value = item['article_id']  # 후보 상품 번호를 읽는다.

        expected = f'images/{value[:3]}/{value}.jpg'  # 허용할 파일 경로를 직접 만든다.

        if not value.isdigit() or len(value) != 10 or item['file_path'] != expected:  # 예상치 못한 경로나 상품 번호를 검사한다.
            raise ValueError('다운로드 목록의 상품 번호 또는 경로가 올바르지 않다.')  # 목록 밖 파일을 받지 않도록 중단한다.

        target = raw / expected  # 저장할 실제 원본 이미지 위치를 지정한다.

        if not has_jpeg_markers(target):  # 이미 받은 정상 파일이면 다운로드를 건너뛴다.
            if target.exists():  # 기존 파일이 있지만 기본 JPEG 검사에 실패했는지 확인한다.
                raise ValueError('기존 이미지가 기본 검사에 실패했다. 파일을 확인한 뒤 다시 실행해.')  # 사용자의 파일을 임의로 덮어쓰지 않는다.

            reason = fetch_image(command, raw, expected)  # 기존 다운로드 재사용 또는 새 파일 다운로드와 배치를 처리한다.
            if reason is not None:  # 파일을 성공 목록에 넣을 수 없는지 확인한다.
                failed.append(expected)  # 실패한 파일 경로만 기록한다.
                failure_details.append({'file': expected, 'reason': reason})  # 인증 정보 없는 실패 분류를 기록한다.
                consecutive += 1  # 연속 실패 수를 늘린다.
                print(f'현재 실패 {len(failed)}개: {FAILURE_MESSAGES[reason]}', flush=True)  # 원본 출력 대신 고정된 설명을 보여 준다.
                if consecutive >= 5:  # 인증이나 권한 문제로 계속 실패하는지 확인한다.
                    break  # 반복 요청을 멈추고 로그인 상태를 확인하게 한다.
                continue  # 이미지가 없으면 다음 보충 후보로 넘어간다.

        success.append(expected)  # 기본 검사를 통과한 파일만 성공 목록에 넣는다.

        consecutive = 0  # 연속 실패 수를 초기화한다.

        print(f'이미지 준비 {len(success)}/{limit}', flush=True)  # 제한된 다운로드 진행 상태를 알린다.

        if len(success) >= limit:  # 목표 개수를 확보했는지 확인한다.
            break  # 보충 후보를 모두 다운로드하지 않고 멈춘다.


    report = {'target': limit, 'ready': len(success), 'files': success, 'failed': failed, 'failure_details': failure_details, 'validation': 'JPEG start/end markers only; decoding is still required'}  # 원문 오류 없이 성공 수와 실패 분류를 기록한다.

    (sample / 'image_download_summary.json').write_text(json.dumps(report, indent=4) + '\n')  # 키나 토큰 없이 결과를 저장한다.

    if len(success) < limit:  # 목표 개수까지 준비하지 못했는지 확인한다.
        raise SystemExit(f'{len(success)}/{limit}장으로 종료했다. 결과 기록의 failure_details와 위 실패 이유를 확인해.')  # 실패를 로그인 문제로 단정하지 않는다.

    print(f'{limit}장 준비 완료. 모든 픽셀의 정상 여부는 분석 단계에서 확인해야 한다.', flush=True)  # 실제 목표 개수와 검사 범위를 알린다.





if __name__ == '__main__':  # 사용자가 직접 실행했을 때만 네트워크 다운로드를 시작한다.
    download(Path(__file__).resolve().parents[1])  # 프로젝트의 표본 목록을 기준으로 이미지를 준비한다.
