import csv  # CSV 표를 한 줄씩 읽고 쓰는 기본 도구를 가져온다.
import hashlib  # 같은 고객을 다시 고를 수 있도록 고정된 숫자를 만드는 도구를 가져온다.
import heapq  # 모든 고객을 정렬하지 않고 필요한 고객만 고르는 도구를 가져온다.
import itertools  # 상품 종류를 번갈아 선택하는 도구를 가져온다.
import json  # 표본을 만든 기준과 결과를 저장하는 도구를 가져온다.
from pathlib import Path  # 파일과 폴더 경로를 다루는 도구를 가져온다.


def stable_key(value):  # 실행할 때마다 같은 선택 순서를 만드는 함수를 정의한다.
    return hashlib.sha256(('hm-learning-v1:' + value).encode()).hexdigest(), value  # 고정된 기준과 값을 함께 사용한다.


def prepare(root, customer_count=500, candidate_count=200):  # 원본에서 작은 표본과 이미지 후보 목록을 만드는 함수를 정의한다.
    raw = root / 'data' / 'raw'  # 원본이 있는 폴더를 지정한다.
    output = root / 'data' / 'sample'  # 표본을 저장할 별도 폴더를 지정한다.
    names = ['transactions.csv', 'articles.csv', 'image_manifest.csv', 'sampling_summary.json']  # 만들 파일 이름을 정한다.
    if any((output / name).exists() for name in names):  # 기존 표본 파일이 있는지 확인한다.
        raise ValueError('표본 파일이 이미 있으므로 덮어쓰지 않는다.')  # 기존 작업을 보존하며 중단한다.
    customers = set()  # 전체 구매 고객 번호를 중복 없이 모을 공간을 만든다.
    source_rows = 0  # 읽은 전체 거래 행 수를 기록한다.
    source_min, source_max = None, None  # 원본의 시작일과 마지막 날짜를 기록할 공간을 만든다.
    with (raw / 'transactions_train.csv').open(newline='', encoding='utf-8-sig') as stream:  # 원본 거래 표를 읽기 전용으로 연다.
        reader = csv.reader(stream)  # 거래를 한 줄씩 읽도록 준비한다.
        header = next(reader)  # 첫 줄에서 컬럼 이름을 읽는다.
        ci, ai, di = (header.index(name) for name in ['customer_id', 'article_id', 't_dat'])  # 필요한 컬럼의 위치를 찾는다.
        for row in reader:  # 원본 거래를 메모리에 모두 올리지 않고 차례로 읽는다.
            source_rows += 1  # 읽은 거래 수를 하나 늘린다.
            if row[ci]:  # 고객 번호가 있는 거래인지 확인한다.
                customers.add(row[ci])  # 구매 고객 번호를 모은다.
            source_min = min(source_min or row[di], row[di])  # 원본의 가장 이른 날짜를 기록한다.
            source_max = max(source_max or row[di], row[di])  # 원본의 가장 늦은 날짜를 기록한다.
            if source_rows % 4000000 == 0:  # 긴 작업의 진행 상태를 주기적으로 알린다.
                print(f'고객 목록 확인: {source_rows:,}행', flush=True)  # 고객 번호 없이 읽은 행 수만 출력한다.
    selected = set(heapq.nsmallest(customer_count, customers, key=stable_key))  # 전체 구매 고객 중 고정된 해시 순서로 고객을 고른다.
    source_customers = len(customers)  # 전체 구매 고객 수를 기록한다.
    del customers  # 더 이상 필요 없는 전체 고객 목록의 메모리를 돌려준다.
    rows = []  # 선택한 고객의 거래만 모을 공간을 만든다.
    products = set()  # 표본에서 구매된 상품 번호를 모을 공간을 만든다.
    print('선택한 고객의 전체 기간 거래를 추출한다.', flush=True)  # 두 번째 읽기의 목적을 알린다.
    with (raw / 'transactions_train.csv').open(newline='', encoding='utf-8-sig') as stream:  # 같은 원본을 다시 읽기 전용으로 연다.
        reader = csv.reader(stream)  # 이번에도 한 줄씩 읽도록 준비한다.
        next(reader)  # 이미 확인한 컬럼 이름 줄을 건너뛴다.
        for index, row in enumerate(reader, 1):  # 모든 기간의 거래를 다시 확인한다.
            if row[ci] in selected:  # 선택한 고객의 거래인지 확인한다.
                row[ai] = row[ai].zfill(10)  # 표본의 상품 번호를 이미지 경로에 맞는 10자리 문자열로 통일한다.
                rows.append(row)  # 거래의 반복 행도 삭제하지 않고 보존한다.
                products.add(row[ai])  # 거래와 연결되는 상품을 기록한다.
            if index % 4000000 == 0:  # 긴 작업의 진행 상태를 주기적으로 알린다.
                print(f'표본 거래 추출: {index:,}행 확인', flush=True)  # 민감한 거래 내용 없이 진행 상태를 출력한다.
    if len(rows) < 1000:  # 과제의 최소 거래 건수를 확인한다.
        raise ValueError('표본이 1,000행 미만이다. 고객 수를 늘려야 한다.')  # 조건을 만족하지 않으면 결과를 만들지 않는다.
    articles = []  # 표본 거래와 연결되는 상품 정보만 모을 공간을 만든다.
    with (raw / 'articles.csv').open(newline='', encoding='utf-8-sig') as stream:  # 원본 상품 표를 읽기 전용으로 연다.
        reader = csv.DictReader(stream)  # 상품을 컬럼 이름으로 읽도록 준비한다.
        article_header = reader.fieldnames  # 상품 표의 컬럼 순서를 보존한다.
        for article in reader:  # 상품 정보를 하나씩 확인한다.
            article['article_id'] = article['article_id'].zfill(10)  # 표본의 상품 번호 자릿수를 거래와 맞춘다.
            if article['article_id'] in products:  # 표본에서 구매된 상품인지 확인한다.
                articles.append(article)  # 필요한 상품 정보만 모은다.
    if {article['article_id'] for article in articles} != products:  # 모든 표본 상품이 상품 표에 연결되는지 확인한다.
        raise ValueError('상품 표에 연결되지 않는 거래 상품이 있다.')  # 잘못 연결된 상태로 다운로드 목록을 만들지 않는다.
    groups = {}  # 상품 종류별로 이미지 후보를 모을 공간을 만든다.
    for article in sorted(articles, key=lambda item: stable_key(item['article_id'])):  # 상품 후보의 순서를 고정한다.
        groups.setdefault(article['product_group_name'], []).append(article['article_id'])  # 상품 종류별 목록에 상품을 넣는다.
    candidates = []  # 실제 이미지 파일 경로 후보를 모을 공간을 만든다.
    for batch in itertools.zip_longest(*(groups[key] for key in sorted(groups))):  # 종류별 상품을 번갈아 고른다.
        candidates.extend(value for value in batch if value is not None)  # 상품이 남아 있는 종류의 후보를 모은다.
        if len(candidates) >= candidate_count:  # 보충 후보까지 필요한 수를 모았는지 확인한다.
            break  # 불필요한 후보 추가를 멈춘다.
    candidates = candidates[:candidate_count]  # 후보 목록의 최대 개수를 제한한다.
    dates = [row[di] for row in rows]  # 표본의 기간을 확인하기 위해 날짜만 모은다.
    summary = {'selection': 'SHA-256 hm-learning-v1; entire customer history; repeated rows preserved', 'source_rows': source_rows, 'source_customers': source_customers, 'source_date_min': source_min, 'source_date_max': source_max, 'sample_customers': len(selected), 'sample_rows': len(rows), 'sample_articles': len(articles), 'sample_date_min': min(dates), 'sample_date_max': max(dates), 'image_candidates': len(candidates), 'image_success_target': 100, 'joined_columns': len(set(header) | set(article_header))}  # 표본 기준과 집계 수치를 기록한다.
    output.mkdir(parents=True, exist_ok=True)  # 원본과 별개인 표본 폴더를 만든다.
    with (output / names[0]).open('w', newline='', encoding='utf-8') as stream:  # 표본 거래 파일을 만든다.
        writer = csv.writer(stream)  # 표를 저장할 도구를 준비한다.
        writer.writerow(header)  # 거래 컬럼 이름을 저장한다.
        writer.writerows(rows)  # 선택 고객의 전체 기간 거래를 저장한다.
    with (output / names[1]).open('w', newline='', encoding='utf-8') as stream:  # 표본 상품 파일을 만든다.
        writer = csv.DictWriter(stream, fieldnames=article_header)  # 원본과 같은 상품 컬럼 순서를 사용한다.
        writer.writeheader()  # 상품 컬럼 이름을 저장한다.
        writer.writerows(articles)  # 필요한 상품 정보만 저장한다.
    with (output / names[2]).open('w', newline='', encoding='utf-8') as stream:  # 이미지 다운로드 목록을 만든다.
        writer = csv.writer(stream)  # 목록을 표로 저장할 도구를 준비한다.
        writer.writerow(['article_id', 'file_path'])  # 상품 번호와 다운로드 경로 컬럼을 만든다.
        writer.writerows((value, f'images/{value[:3]}/{value}.jpg') for value in candidates)  # 후보 상품에 연결되는 파일 경로를 저장한다.
    (output / names[3]).write_text(json.dumps(summary, ensure_ascii=False, indent=4) + '\n')  # 고객 번호 없이 표본 요약을 저장한다.
    print(json.dumps(summary, ensure_ascii=False, indent=4), flush=True)  # 비밀 정보 없이 결과의 규모를 알린다.
    return summary  # 검증할 수 있도록 요약 결과를 반환한다.


if __name__ == '__main__':  # 파일을 직접 실행했을 때만 원본을 처리한다.
    prepare(Path(__file__).resolve().parents[1])  # 프로젝트 위치를 기준으로 기본 규모의 표본을 만든다.
