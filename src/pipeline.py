import hashlib  # 입력 파일의 재현용 비교값을 계산한다.
import io  # 개인정보 없이 표 구조 설명을 모은다.
import json  # 분석 기준과 집계 결과를 저장한다.
import os  # Matplotlib의 캐시 위치를 프로젝트 안으로 정한다.
from pathlib import Path  # 데이터 파일 경로를 다룬다.

# numpy (숫자를 다루는 핵심 라이브러리. pandas도 numpy를 기반으로 만들어졌다.)
import numpy as np  # 픽셀과 숫자를 배열 연산으로 처리한다.


# pandas (표. 행과 열로 이루어진 데이터 구조를 다룬다. )
# pandas를 jupyter notebook에서 돌아가게 하지 않고 이렇게 별도의 파이썬 코드에서 돌라가게 import를 해놨다.
import pandas as pd  # 표 연결과 그룹별 계산을 처리한다.


# matplotlib : 그래프 그리는 라이브러리
# 캐시를 사용자 홈에 쓰지 않도록 기본 위치를 정한다.
os.environ.setdefault('MPLCONFIGDIR', str(Path(__file__).resolve().parents[1] / '.cache/matplotlib'))  
from matplotlib.image import imread  # 과제에서 허용한 이미지 입력 함수만 가져온다.


# -----------------------------------------------------
# 차트와 보고서에서 같은 고객 그룹 순서를 사용한다.
SEGMENTS = ['Recent buyers / Frequent & high spending', 'Recent buyers / Less frequent or lower spending', 'No recent purchase / Frequent & high spending', 'No recent purchase / Less frequent or lower spending']


# -----------------------------------------------------
class DataAnalyzer:  # 데이터를 읽고 분석하는 기능을 하나의 도구 상자에 묶는다.
    def __init__(self, data_path='data/sample', image_dir='data/raw/images', min_rows=1000):  # 입력 위치와 최소 행 수를 받는다.
        self.data_path = Path(data_path)  # 표본 CSV 위치를 보관한다.
        self.image_dir = Path(image_dir)  # 실제 이미지 위치를 보관한다.
        self.min_rows = min_rows  # 작은 테스트에서는 최소 행 수를 조정할 수 있게 한다.
        self.df = None  # 연결한 거래 표는 데이터를 읽은 뒤 채운다.
        self.audit = {}  # 처리 기준과 검사 결과를 모은다.
        self.rfm = None  # 고객별 분석 결과는 나중에 계산한다.


    # ✅ [load_data] 상품번호 자릿수 통일
    @staticmethod  # 상품 번호 정리는 객체 상태를 바꾸지 않는 공통 기능이다.
    def normalize_ids(values):  # 상품 번호를 앞의 0이 있는 문자열로 맞춘다.
        normalized = values.astype('string').str.strip()  # 계산용 숫자 대신 문자열로 읽는다.
        if normalized.isna().any() or not normalized.str.fullmatch(r'[0-9]{1,10}').all():  # 빈 값과 예상 밖 상품 번호를 막는다.
            raise ValueError('상품 번호는 비어 있지 않은 1~10자리 숫자 문자열이어야 한다.')  # 실제 값을 노출하지 않고 오류를 알린다.
        return normalized.str.zfill(10)  # 부족한 왼쪽 자리를 0으로 채운다.

    
    # ✅
    def load_data(self):  # 거래와 상품을 연결하고 기본 구조를 검사한다.
        
        # 🔥🔥🔥🔥🔥
        transactions_path = self.data_path / 'transactions.csv'  # 분석용 거래 표본을 선택한다.
        articles_path = self.data_path / 'articles.csv'  # 거래와 연결할 상품 표본을 선택한다.
        
        if not transactions_path.is_file() or not articles_path.is_file():  # 준비 단계가 빠졌는지 확인한다.
            raise ValueError('거래·상품 표본이 없다. 원본·표본 준비부터 확인하세요.')  # 개인 절대 경로 없이 필요한 작업을 알린다.
        

        # 🔥🔥🔥🔥🔥
        transactions = pd.read_csv(transactions_path, dtype={'article_id': 'string', 'customer_id': 'string'})  # 고객·상품 식별자의 문자열을 보존한다.
        
        articles = pd.read_csv(articles_path, dtype={'article_id': 'string'})  # 상품 번호 앞의 0을 보존한다.
        
        transaction_columns = {'customer_id', 'article_id', 't_dat', 'price', 'sales_channel_id'}  # 필수 거래 컬럼을 정한다.
        
        article_columns = {'article_id', 'product_group_name', 'prod_name', 'detail_desc'}  # 특성 계산에 필요한 상품 컬럼을 정한다.
        
        if not transaction_columns <= set(transactions) or not article_columns <= set(articles):  # 잘못된 CSV를 받은 경우를 막는다.
            raise ValueError('거래 또는 상품 표에 분석 필수 컬럼이 없다.')  # 데이터 내용 대신 구조 오류만 알린다.
        
        if len(transactions) < self.min_rows or transactions['customer_id'].isna().any() or transactions['customer_id'].str.strip().eq('').any():  # 거래 규모와 고객 연결 기준을 확인한다.
            raise ValueError('최소 거래 수 또는 비어 있지 않은 고객 번호 조건을 만족하지 않는다.')  # 잘못된 상태로 고객 분석을 진행하지 않는다.
        

        # 🔥🔥🔥🔥🔥
        transactions['article_id'] = self.normalize_ids(transactions['article_id'])  # 거래 상품 번호를 통일한다.
        
        articles['article_id'] = self.normalize_ids(articles['article_id'])  # 상품 표 번호를 거래와 같은 형태로 맞춘다.
        
        if articles['article_id'].duplicated().any():  # 상품 중복으로 거래 행이 늘어나는 위험을 확인한다.
            raise ValueError('상품 번호가 중복됐다. 상품 하나에 정보 한 행이 필요하다.')  # 임의로 첫 상품만 고르지 않고 중단한다.
        

        # 🔥🔥🔥🔥🔥
        transactions['order_date'] = pd.to_datetime(transactions['t_dat'], format='%Y-%m-%d', errors='raise')  # 날짜를 계산 가능한 자료형으로 바꾼다.
        transactions['price'] = pd.to_numeric(transactions['price'], errors='raise')  # 가격을 숫자로 변환한다.
        
        if transactions['order_date'].isna().any() or not np.isfinite(transactions['price']).all() or transactions['price'].lt(0).any():  # 잘못된 날짜와 가격이 금액 분석에 들어가지 않게 한다.
            raise ValueError('날짜 누락 또는 유한한 0 이상 가격 조건을 만족하지 않는다.')  # 가격을 임의 대치하지 않고 중단한다.
        
        
        # 🔥🔥🔥🔥🔥
        transactions['amount'] = transactions['price']  # 한 구매 행의 원본 가격을 분석용 금액으로 정의한다.
        overlap = (set(transactions) & set(articles)) - {'article_id'}  # 상품 연결 시 뜻이 바뀔 수 있는 컬럼 충돌을 확인한다.
        
        if overlap:  # 같은 이름의 다른 정보가 있을 때 중단한다.
            raise ValueError('거래와 상품 표에 상품 번호 이외의 중복 컬럼이 있다.')  # 자동 접미사로 문제를 숨기지 않는다.
        

        # 🔥🔥🔥🔥🔥
        joined = transactions.merge(articles, on='article_id', how='left', validate='many_to_one', indicator=True)  # 거래 여러 행에 상품 정보 한 행을 연결한다.
        
        if not joined['_merge'].eq('both').all():  # 모든 구매 상품에 상품 정보가 있는지 확인한다.
            raise ValueError('상품 정보에 연결되지 않는 거래가 있다.')  # 빠진 거래를 조용히 삭제하지 않는다.
        
        
        self.df = joined.drop(columns='_merge')  # 연결 검사용 컬럼만 제거한다.
        self.articles = articles.copy(deep=True)  # 상품 단위 검사용 원본 사본을 보관한다.
        self.raw_df = self.df.copy(deep=True)  # 전처리 전 표를 비교용으로 보관한다.
        self.audit = {'rows': len(self.df), 'customers': int(self.df['customer_id'].nunique()), 'products': int(self.df['article_id'].nunique()), 'joined_columns': len(set(transaction_columns) | set(articles.columns)), 'date_min': self.df['order_date'].min().date().isoformat(), 'date_max': self.df['order_date'].max().date().isoformat(), 'repeated_rows_preserved': int(transactions.duplicated(subset=list(transaction_columns)).sum())}  # 고객 번호 없이 집계만 기록한다.
        self.audit['source_hashes'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in [transactions_path, articles_path]}  # 작은 표본 입력의 출처 비교값을 기록한다.
        self.audit['missing_before'] = self.df.isna().sum().astype(int).to_dict()  # 실제 결측치 개수를 기록한다.
        self.rfm = None  # 새 데이터를 읽으면 이전 고객 분석 결과를 초기화한다.
        
        return self.df  # 직접 확인하거나 다음 계산에 사용할 표를 반환한다.


    # ✅ 상품 글을 분석 가능한 숫자로 바꾼다. (글자 수 계산)
    def add_text_features(self):  # 상품 글을 분석 가능한 숫자로 바꾼다.
        self.df['product_name_length'] = self.df['prod_name'].astype('string').str.len().astype(float)  # 상품명 문자 수를 계산한다.
        self.df['product_name_words'] = self.df['prod_name'].astype('string').str.split().str.len().astype(float)  # 공백 기준 상품명 단어 수를 계산한다.
        self.df['description_length'] = self.df['detail_desc'].astype('string').str.len().astype(float)  # 실제로 없는 설명의 길이는 결측치로 남긴다.
        return self.df  # 새 특성이 붙은 표를 반환한다.


    # ✅ 결측치 - 상품 그룹 통계로 빠진 상품 특성을 채운다.
    def handle_missing_values(self, column='description_length', group_col='product_group_name', strategy='group_median'):
        if strategy not in {'group_mean', 'group_median'}:  # 지원하는 대치 기준만 허용한다.
            raise ValueError('strategy는 group_mean 또는 group_median이어야 한다.')  # 모르는 전략을 임의로 적용하지 않는다.
        base = self.df[['article_id', group_col, column]].drop_duplicates()  # 같은 구매가 많아도 상품 통계를 중복 가중하지 않는다.
        if base['article_id'].duplicated().any():  # 상품 단위에서 값이 달라지는 가격 같은 컬럼인지 확인한다.
            raise ValueError('이 대치 함수에는 상품별 값이 하나인 수치 특성을 사용해.')  # 거래 가격을 상품 설명처럼 대치하지 않는다.
        original_missing = self.df[column].isna()  # 어떤 거래 행의 특성이 원래 비었는지 보관한다.
        reducer = 'mean' if strategy == 'group_mean' else 'median'  # 선택한 통계 함수 이름을 정한다.
        grouped = base.groupby(group_col, dropna=False)[column].transform(reducer)  # 같은 상품군에 속한 상품의 대표값을 계산한다.
        fallback = base[column].agg(reducer)  # 해당 상품군 전체가 비었을 때 쓸 전체 상품 대표값을 계산한다.
        if pd.isna(fallback):  # 컬럼 전체가 비어서 근거 있는 대치가 불가능한지 확인한다.
            raise ValueError('전체 상품 특성이 비어 있어 통계 대치를 할 수 없다.')  # 0 같은 가짜 관측값을 넣지 않는다.
        filled = base[column].fillna(grouped).fillna(fallback)  # 그룹 통계 다음 전체 통계 순서로 대치한다.
        mapping = pd.Series(filled.to_numpy(), index=base['article_id'])  # 상품별 계산 결과를 연결할 표로 만든다.
        self.df[column + '_was_missing'] = original_missing  # 관측한 값과 대치한 값을 구분한다.
        self.df[column] = self.df['article_id'].map(mapping).astype(float)  # 상품별 대표값을 모든 연결 거래에 붙인다.
        self.audit['imputation'] = {'column': column, 'group': group_col, 'strategy': strategy, 'missing_products': int(base[column].isna().sum()), 'filled_transaction_rows': int(original_missing.sum()), 'global_fallback_products': int((base[column].isna() & grouped.isna()).sum()), 'remaining': int(self.df[column].isna().sum())}  # 대치 규모와 기준을 기록한다.
        return self.df  # 대치 결과를 반환한다.

    
    # ✅ IQR 이상치 범위를 직접 계산한다.
    def detect_outliers(self, column='price', threshold=1.5): 
        if not np.isfinite(threshold) or threshold <= 0:  # 잘못된 이상치 배율을 막는다.
            raise ValueError('이상치 배율은 유한한 양수여야 한다.')  # 음수 배율로 경계가 뒤집히지 않게 한다.
        
        values = pd.to_numeric(self.df[column], errors='raise')  # 검사할 숫자 컬럼을 선택한다.
        
        # 🔥 25%, 75%에 해당하는 사분위수 구하기
        first, third = values.quantile([0.25, 0.75]).to_numpy()  # 아래·위 사분위수를 계산한다.
        
        # 🔥 25%, 75% 구한 값으로 중앙값(50%)을 찾음
        # Q1·Q3을 구하고 IQR(Interquartile Range, 사분위 범위)=Q3−Q1로 계산
        spread = third - first  # 가운데 50퍼센트 구간의 폭을 계산한다.
        
        # 🔥 하한선과 상한선 구하기
        # threshold 곱함 -> 사분위 범위를 1.5배 늘림 -> 극단적인 값만 이상치로 탐지
        lower, upper = first - threshold * spread, third + threshold * spread  # 이상치의 아래·위 경계를 직접 만든다.
        
        # 🔥 이상치 탐지
        mask = values.lt(lower) | values.gt(upper)  # 경계 밖의 거래 행을 찾는다.
        
        self.df[column + '_is_outlier'] = mask  # 이상치 여부를 표시하되 거래를 지우지 않는다.
        self.df[column + '_clipped'] = values.clip(lower=lower, upper=upper)  # 분포 비교용으로만 경계값에 맞춘 복사 컬럼을 만든다.
        self.audit['outliers'] = {'column': column, 'factor': float(threshold), 'q1': float(first), 'q3': float(third), 'iqr': float(spread), 'lower': float(lower), 'upper': float(upper), 'count': int(mask.sum()), 'policy': 'flag; clipped copy for comparison; original amount preserved for RFM'}  # 처리 기준을 남긴다.
        return mask  # 어떤 행이 범위 밖인지 반환한다.


    # ✅ 이미지 관련 기능
    @staticmethod  # 픽셀 계산은 파일이나 고객 자료 없이 검사할 수 있는 기능이다.
    def image_statistics(image):  # 한 이미지의 배열에서 통계 특성을 계산한다.
        array = np.asarray(image)  # 이미지 입력을 NumPy 배열로 다룬다.
        if array.ndim == 2:  # 흑백 이미지인지 확인한다.
            array = np.repeat(array[:, :, None], 3, axis=2)  # 흑백 값을 RGB 세 채널로 맞춘다.
        if array.ndim != 3 or array.shape[2] not in {3, 4} or min(array.shape[:2]) == 0:  # 지원하는 이미지 모양인지 확인한다.
            raise ValueError('이미지는 비어 있지 않은 흑백·RGB·RGBA 배열이어야 한다.')  # 잘못된 배열을 조용히 해석하지 않는다.
        pixels = array[:, :, :3].astype(np.float64)  # 알파 채널을 제외한 RGB 계산 사본을 만든다.
        
        # 🔥🔥🔥🔥🔥 0~1로 만드는 이유 = 딥러닝 모델 학습 시 0~255 범위보다 0~1 범위가 수렴 속도가 빠르고 안정적이기 때문.
        # 이미지 픽셀에서 흔히 쓰는 uint8은 8비트 숫자로 2^8 = 256개 값을 표현할 수 있다. (0부터 시작하니 255까지 표현가능!)
        # 255는 한 색상 채널이 가질 수 있는 최대 밝기 값인 것이다.
        if np.issubdtype(array.dtype, np.integer):  # JPEG처럼 정수 픽셀로 읽었는지 확인한다.
            pixels /= np.iinfo(array.dtype).max  # 자료형 최댓값을 기준으로 0~1 범위로 맞춘다.
            # array.dtype: array의 자료형 확인
            # np.iinfo: 정수형의 최댓값과 최솟값을 반환하는 함수
                # np.iinfo(np.uint8).max = 255
                # np.iinfo(np.int32).max = 2147483647
            # pixels 배열의 모든 값을, 원본 정수 자료형이 가질 수 있는 최댓값으로 나눈 뒤 다시 pixels에 저장한다!!!
        
        if not np.isfinite(pixels).all() or pixels.min() < 0 or pixels.max() > 1:  # 정상적인 밝기 범위를 확인한다.
            raise ValueError('픽셀 값이 유한한 0~1 범위가 아니다.')  # 잘못된 값을 특성으로 저장하지 않는다.
        
        # 🔥🔥🔥🔥🔥 피처 설명
        # mean - 이미지 평균 밝기: 낮으면 어두운 상품, 높으면 밝은 상품
        # std - 이미지 표준편차: 낮으면 색상/밝기가 균일, 높으면 색상/밝기 대비가 큼
        # height/width - 이미지 크기: 다양한 디바이스에 대응하기 위해
        return {'image_mean': float(np.mean(pixels)), 'image_std': float(np.std(pixels, ddof=0)), 'image_height': int(array.shape[0]), 'image_width': int(array.shape[1])}  # 픽셀 반복문 없이 전체 배열 통계를 계산한다.


    # ✅ 이미지 관련 기능
    def add_image_features(self, min_images=100):  # 받은 실제 이미지의 통계를 상품별로 연결한다.
        if min_images < 0:  # 음수 목표를 막는다.
            raise ValueError('최소 이미지 수는 0 이상이어야 한다.')     # 잘못된 입력을 알린다.
        
        products = set(self.df['article_id'])                   # 구매 상품에 연결되는 이미지인지 확인할 기준을 만든다.
        
        records, failures = [], []                              # 상품 특성과 읽기 실패를 따로 모은다.
        
        for path in sorted(self.image_dir.glob('*/*.jpg')):     # 파일 입출력은 파일별로 하되 픽셀 계산은 배열로 처리한다.
            if path.stem not in products or path.parent.name != path.stem[:3]:  # 표본 밖 파일이나 잘못된 위치를 제외한다.
                continue  # 실제 분석 상품에 연결되는 파일만 사용한다.
            try:  # 마커 검사만 통과한 손상 이미지도 여기서 걸러낸다.
                features = self.image_statistics(imread(path))  # 실제 디코딩 후 NumPy로 통계를 계산한다.
            except (ValueError, OSError, SyntaxError):          # 해석하지 못한 파일은 별도 기록한다.
                failures.append({'article_id': path.stem, 'reason': 'decode_error'})  # 오류 원문과 절대 경로는 기록하지 않는다.
                continue  # 다른 정상 이미지는 계속 검사한다.
            records.append({'article_id': path.stem, **features})  # 상품 번호와 계산 결과를 연결한다.
        
        columns = ['article_id', 'image_mean', 'image_std', 'image_height', 'image_width']  # 결과가 없을 때도 일정한 헤더를 만든다.
        
        features = pd.DataFrame(records, columns=columns)       # 상품당 한 행의 이미지 특성 표를 만든다.
        
        if len(features) < min_images:                          # 준비한 이미지가 목표에 못 미치는지 확인한다.
            raise ValueError(f'실제로 해석한 이미지가 {len(features)}개다. 최소 {min_images}개가 필요하다.')  # 형식 검사 성공과 실제 디코딩 성공을 구분한다.
        
        self.df = self.df.merge(features, on='article_id', how='left', validate='many_to_one')  # 사진 없는 상품도 거래 표에 그대로 남긴다.
        self.df['has_image'] = self.df['image_mean'].notna()    # 이미지가 실제로 연결됐는지 표시한다.
        self.audit['images'] = {'decoded_products': len(features), 'failed': failures, 'covered_transaction_rows': int(self.df['has_image'].sum()), 'coverage_fraction': float(self.df['has_image'].mean()), 'mean_range': [0, 1], 'std_ddof': 0}  # 이미지가 있는 부분의 크기를 기록한다.
        
        return features  # 상품별 이미지 특성을 반환한다.







    # ✅ RFM 고객 특성 계산
    def calculate_rfm(self, customer_col='customer_id', date_col='order_date', amount_col='amount', reference_date=None, frequency='purchase_rows'):  # 전체 구매 이력으로 고객 특성을 계산한다.

        # 🟢 1. 구매 빈도(F)의 단위를 먼저 정한다.
        # 'purchase_rows': 구매 기록의 행 수. 같은 날 세 행이 있으면 3이다.
        # 'purchase_days': 구매한 날짜의 종류 수. 같은 날 세 행이면 1이다.
        # 예: 9월 20일에 두 행, 9월 21일에 한 행 → purchase_rows=3, purchase_days=2.
        # 이 데이터에는 주문 번호가 없으므로 행 수를 정확한 주문 횟수라고 부르면 안 된다.
        # 함수 기본값은 purchase_rows이므로 따로 지정하지 않으면 행 수가 F가 된다.
        # not in은 '허용된 두 문자열 중 어느 것도 아닌가?'를 확인하는 파이썬 표현이다.
        if frequency not in {'purchase_rows', 'purchase_days'}:  # 주문 수로 잘못 부르지 않게 허용하는 단위를 정한다.
            raise ValueError('구매 빈도는 purchase_rows 또는 purchase_days로 지정해.')  # 없는 주문 번호를 만들지 않는다.

        # 🟢 2. 모든 고객에게 똑같이 적용할 기준일을 정한다.
        # R은 '기준일 - 고객의 마지막 구매일'이므로 기준일이 먼저 필요하다.
        # self.df[date_col]: 날짜 열 전체를 선택하는 pandas 표현이다.
        # .max(): 그 열에서 가장 늦은 날짜를 고르는 pandas 메서드다.
        # A if 조건 else B: 조건이 참이면 A, 아니면 B를 선택하는 파이썬 표현이다.
        # 따라서 기준일을 생략하면 표본의 마지막 날짜를 사용하고,
        # 기준일을 직접 넣으면 pd.Timestamp()로 날짜 계산에 쓸 수 있게 바꾼다.
        # pd.Timestamp('2020-09-22')는 문자열을 pandas 날짜 값으로 바꾼 예다.
        # 오늘 날짜를 자동으로 쓰지 않으므로 같은 과거 자료는 같은 기준으로 재현할 수 있다.
        # 기준일 자체가 고객마다 달라지는 것은 아니다. 모든 고객이 같은 날짜를 쓴다.
        reference = self.df[date_col].max() if reference_date is None else pd.Timestamp(reference_date)  # 명시한 분석일 또는 마지막 거래일을 기준일로 쓴다.

        # 기준일은 표본에 있는 마지막 구매일보다 이르면 안 된다.
        # 예: 기준일이 9월 20일인데 9월 22일 구매가 있으면 날짜 차이가 -2일이 된다.
        # 이 함수는 입력 자료를 기준일 이전으로 잘라 주지 않으므로 그런 입력을 막는다.
        if reference < self.df[date_col].max():  # 마지막 거래보다 과거인 기준일을 막는다.
            raise ValueError('RFM 기준일은 마지막 거래일보다 이르면 안 된다.')  # 음수 최근 구매 간격을 만들지 않는다.

        # 🟢 3. 같은 고객의 구매 행을 한 묶음으로 모은다.
        # .groupby(customer_col, sort=True)는 pandas의 그룹 묶기 메서드다.
        # customer_col이 'customer_id'이면 고객 번호가 같은 행끼리 묶는다.
        # sort=True는 고객 묶음을 고객 번호 순서로 정렬한다는 뜻이다.
        # 구매 날짜나 점수 순서로 정렬한다는 뜻이 아니다.
        # 이 단계는 묶음만 준비한다. 아직 각 묶음의 합계나 마지막 날짜를 구하지 않았다.
        grouped = self.df.groupby(customer_col, sort=True)  # 같은 고객 번호의 구매 행을 묶어 집계할 준비를 한다.

        # 🟢 4. 고객마다 필요한 숫자를 한 번에 계산한다.
        # .agg()는 pandas의 aggregation(집계) 메서드다.
        # 새_열_이름=(원본_열_이름, 계산_이름) 형태로 결과 열과 계산 방법을 지정한다.
        # last_purchase=(date_col, 'max'): 고객의 날짜 중 가장 늦은 날, 즉 마지막 구매일.
        # purchase_rows=(date_col, 'size'): 고객 묶음에 들어 있는 행의 개수.
        # purchase_days=(date_col, 'nunique'): 날짜 값이 서로 다른 종류의 개수.
        # monetary=(amount_col, 'sum'): 고객의 모든 구매 금액을 더한 값.
        # nunique는 number of unique values, 즉 서로 다른 값의 개수를 구한다.
        # 여기서는 order_date가 날짜 단위라서 같은 날 여러 구매는 구매일 하나로 센다.
        #
        # 예: 고객 A에게 다음 세 행이 있다고 생각해 보자.
        # 2020-09-20 / 금액 0.01
        # 2020-09-20 / 금액 0.02
        # 2020-09-21 / 금액 0.03
        # A의 결과는 마지막 구매일=9월 21일, 구매 행=3, 구매일=2, 금액 합계=0.06이다.
        # 결과 표 result는 고객마다 한 행이며 고객 번호는 아직 index(행 이름)에 있다.
        # 이 프로젝트의 amount는 원본 price를 복사한 값이다.
        # M은 price_clipped가 아니라 원본 금액을 더한다. 이상치 가격도 원본대로 포함한다.
        # 원본 가격 단위를 그대로 쓰며 원화나 달러로 임의 해석하지 않는다.
        result = grouped.agg(last_purchase=(date_col, 'max'), purchase_rows=(date_col, 'size'), purchase_days=(date_col, 'nunique'), monetary=(amount_col, 'sum'))  # 구매 행·구매일·금액을 함께 계산한다.

        # 🟢 5. R(Recency): 마지막 구매로부터 지난 일수를 계산한다.
        # 기준일에서 고객별 마지막 구매일을 빼면 날짜 차이가 나온다.
        # .dt는 pandas 날짜·시간 관련 기능에 접근하는 속성이다.
        # .dt.days는 날짜 차이에서 '며칠'에 해당하는 정수를 꺼낸다.
        # 예: 기준일 9월 22일 - A의 마지막 구매일 9월 21일 = R 1일.
        # 마지막 구매일이 기준일과 같으면 R은 0이다.
        # R이 작을수록 최근 구매한 고객이다. R이 크다고 더 좋은 고객인 것은 아니다.
        result['recency'] = (reference - result['last_purchase']).dt.days  # 마지막 구매 후 지난 날짜를 계산한다.

        # 🟢 6. F(Frequency): 미리 계산한 두 빈도 중 하나를 선택한다.
        # result[frequency]에서 frequency는 열 이름이 들어 있는 변수다.
        # 기본값이면 result['purchase_rows']를, purchase_days이면 그 열을 읽는다.
        # 예시 고객 A의 F는 기본값일 때 3, purchase_days를 선택하면 2다.
        # M(Monetary)은 위 agg()에서 이미 계산했다. A의 M은 0.06이다.
        # 따라서 기준일이 9월 22일이고 기본 설정이면 A의 RFM은 R=1, F=3, M=0.06이다.
        result['frequency'] = result[frequency]  # 선택한 구매 빈도 단위를 사용한다.

        # 🟢 7. R·F·M을 각각 1~4점으로 표현한다.
        # 점수는 원래 단위가 서로 다른 세 특성을 같은 1~4 범위로 읽기 위한 것이다.
        # 4점은 상대적으로 최근 구매했거나, 빈도가 높거나, 금액이 큰 쪽이다.
        # 1점은 그 반대쪽이다. 임의의 고정 금액 기준을 적용한 점수는 아니다.
        #
        # 아래에서 사용하는 도구의 소속과 역할:
        # .rank(method='average', pct=True): pandas 메서드. 작은 값부터 순위를 매긴다.
        # method='average': 값이 같으면 그 값들이 차지할 순위의 평균을 같이 준다.
        # 예: 1, 2, 2, 4 → 순위는 1, 2.5, 2.5, 4가 된다.
        # pct=True: 순위를 고객 수로 나눈 비율로 돌려준다. pct는 percent의 약자다.
        # 예: 고객 4명의 순위 1, 2, 3, 4 → 비율 0.25, 0.50, 0.75, 1.00.
        # np.ceil(): NumPy 함수. 소수점을 올림한다. 1.2는 2, 2.0은 그대로 2다.
        # .clip(1, 4): pandas 메서드. 1보다 작으면 1, 4보다 크면 4로 제한한다.
        # .astype(int): pandas 메서드. 2.0 같은 숫자를 정수 2로 바꾼다.
        #
        # R은 작을수록 최근이므로 순위 비율의 방향을 1 - 비율로 뒤집는다.
        # 예: 고객 10명 중 R이 가장 작은 고객의 순위 비율이 0.1이면,
        # (1 - 0.1) × 4 = 3.6 → 올림 4 → 범위 제한 4 → 정수 4점.
        # R이 가장 큰 고객은 비율 1.0 → (1 - 1.0) × 4 = 0이다.
        # 이 0을 clip(1, 4)이 1로 바꿔서 최저 점수를 1점으로 맞춘다.
        # 즉 '최근에 구매할수록 높은 R 점수'가 되도록 계산한다.
        #
        # 주의: 네 점수에 고객이 정확히 25%씩 들어간다는 보장은 없다.
        # 같은 값에는 같은 평균 순위를 주므로 특정 점수에 고객이 몰릴 수 있다.
        # R은 비율을 뒤집고 최솟값을 보정하므로 F·M과 경계 배정도 완전히 같지 않다.
        # '4점은 반드시 정확히 상위 25%'라고 단정하지 말고 상대적 순위 점수로 읽는다.
        result['r_score'] = np.ceil((1 - result['recency'].rank(method='average', pct=True)) * 4).clip(1, 4).astype(int)  # 같은 값의 고객은 같은 최근 구매 점수를 받는다.

        # F는 클수록 빈도가 높으므로 순위 비율을 뒤집지 않는다.
        # 예: 고객 10명 중 F가 낮아서 순위 비율이 0.1이면 0.1 × 4 = 0.4 → 올림 1점.
        # 순위 비율이 0.8이면 0.8 × 4 = 3.2 → 올림 4점.
        # method='average' 덕분에 구매 빈도가 같은 고객끼리는 같은 F 점수를 받는다.
        result['f_score'] = np.ceil(result['frequency'].rank(method='average', pct=True) * 4).clip(1, 4).astype(int)  # 구매 빈도 순위를 네 단계 점수로 바꾼다.

        # M도 클수록 금액 합계가 크므로 F와 같은 방식으로 계산한다.
        # 고객의 총금액 순위 비율 × 4 → 올림 → 1~4 제한 → 정수 변환 순서다.
        # 금액 그 자체를 4배 늘리거나, 원본 금액을 바꾸는 작업은 아니다.
        # 여기까지는 원래 R·F·M 열 옆에 점수 열 세 개를 추가한 것이다.
        result['m_score'] = np.ceil(result['monetary'].rank(method='average', pct=True) * 4).clip(1, 4).astype(int)  # 금액 순위를 네 단계 점수로 바꾼다.

        # 🔥🔥🔥🔥🔥 
        # 🟢 8. 네 그룹으로 나누기 위한 기준값을 별도로 구한다.
        # 여기부터는 앞의 r_score / f_score / m_score를 사용하지 않는다.
        # 고객별 원래 R·F·M의 median(중앙값)을 각각 기준으로 사용한다.
        # .median()은 pandas 메서드이며, 값을 크기순으로 놓았을 때 가운데 값이다.
        # 고객 수가 짝수면 가운데 두 값의 평균을 사용한다.
        # float()는 파이썬 기본 함수이며, 결과를 소수 표현이 가능한 숫자로 바꾼다.
        # cut은 여기서 '구분 기준값'이라는 뜻으로 붙인 변수 이름이다.
        # 기준은 거래 행마다 구하는 것이 아니라 고객마다 한 행인 result에서 구한다.
        # 예: 고객별 R이 2, 5, 10, 30, 60이면 recency_cut은 10일이다.
        recency_cut = float(result['recency'].median())  # 표본 고객 중앙값을 최근 구매 기준으로 정한다.

        # 고객별 F가 1, 2, 4, 8, 12라면 frequency_cut은 4다.
        # 기본 설정에서는 4개 구매 행이 기준이고, purchase_days 설정이면 4개 구매일이 기준이다.
        frequency_cut = float(result['frequency'].median())  # 표본의 구매 빈도 중앙값을 계산한다.

        # 고객별 M이 0.02, 0.05, 0.10, 0.30, 0.50이면 monetary_cut은 0.10이다.
        # 위 숫자들은 계산 원리를 보여 주기 위한 가상 예시다.
        # 실제 기준은 입력한 고객 표본으로 매번 계산하므로 데이터가 달라지면 달라진다.
        monetary_cut = float(result['monetary'].median())  # 표본의 금액 중앙값을 계산한다.

        # 🟢 9. 각 고객이 어떤 조건에 해당하는지 True / False로 표시한다.
        # .le(기준)은 pandas 메서드이며 less than or equal, 즉 <=와 같다.
        # recent는 고객마다 'R이 중앙값 이하인가?'를 기록한 참/거짓 목록이다.
        # 예: R 기준이 10일이면 R=2와 R=10은 True, R=30은 False다.
        # 기준값과 똑같은 고객도 최근 그룹에 포함한다.
        # 최근이라는 말은 이번 표본 중앙값에 비해 최근이라는 상대적 뜻이다.
        recent = result['recency'].le(recency_cut)  # 이 데이터 기간 안에서 상대적으로 최근에 온 고객을 찾는다.

        # .ge(기준)은 pandas 메서드이며 greater than or equal, 즉 >=와 같다.
        # &는 pandas의 고객별 조건을 AND(그리고)로 결합하는 연산자다.
        # valuable=True가 되려면 'F가 중앙값 이상'과 'M이 중앙값 이상'을 모두 만족해야 한다.
        # 예: F 기준 4, M 기준 0.10일 때 F=8/M=0.30이면 True다.
        # F=8/M=0.05이면 빈도가 높아도 금액이 낮으므로 False다.
        # F=2/M=0.30이면 금액이 높아도 빈도가 낮으므로 False다.
        # 그래서 valuable=False는 F와 M이 둘 다 낮다는 뜻이 아니다.
        # 둘 중 하나라도 기준보다 낮으면 False다. 기준과 같은 값은 높은 쪽에 포함된다.
        valuable = result['frequency'].ge(frequency_cut) & result['monetary'].ge(monetary_cut)  # 빈도와 금액이 모두 중앙값 이상인 고객을 구분한다.

        # 🟢 10. 두 조건의 조합으로 네 그룹 이름을 붙인다.
        # ~는 pandas의 True / False를 반대로 뒤집는다. ~recent는 최근 조건을 만족하지 않는 고객이다.
        # ~valuable은 '빈도나 금액 중 하나 이상이 기준보다 낮음'이라는 뜻이다.
        # np.select(조건 목록, 이름 목록, default=기본 이름)는 NumPy 함수다.
        # 고객마다 조건을 앞에서부터 확인해서 처음 True가 된 조건의 이름을 넣는다.
        # 조건이 모두 False이면 default에 지정한 이름을 넣는다.
        # SEGMENTS는 파일 위쪽에서 정의한 네 영어 그룹 이름의 목록이다.
        # SEGMENTS[:3]은 파이썬 슬라이싱으로 앞의 세 이름을 선택한다.
        # SEGMENTS[3]은 0부터 센 네 번째 이름을 선택한다.
    
        # 예: 기준이 R=10일, F=4행, M=0.10이라면 다음처럼 분류된다.
        # A: R=2,  F=8,  M=0.30 → 최근 구매 + 높은 빈도·금액.
        # B: R=5,  F=2,  M=0.05 → 최근 구매 + 빈도나 금액이 낮음.
        # C: R=30, F=12, M=0.50 → 최근 구매 없음 + 높은 빈도·금액.
        # D: R=60, F=1,  M=0.02 → 최근 구매 없음 + 빈도나 금액이 낮음.
        # 이것은 구매 행동을 구분한 이름이다. 실제 신규 고객·이탈 고객이라고 확정하지 않는다.
        # 따라서 세 점수를 합산해서 그룹을 정한다고 설명하면 이 코드와 맞지 않는다.
        result['segment'] = np.select([recent & valuable, recent & ~valuable, ~recent & valuable], SEGMENTS[:3], default=SEGMENTS[3])  # 의미가 겹치지 않는 네 그룹으로 나눈다.

        # 🟢 11. 계산 결과를 분석 객체에 보관한다.
        # .reset_index()는 pandas 메서드로, 행 이름에 있던 고객 번호를 일반 열로 옮긴다.
        # self.rfm에 저장하면 함수 밖에서도 analyzer.rfm으로 결과를 다시 사용할 수 있다.
        # 고객별 번호가 있는 상세 결과는 로컬 분석용이고 공개 그래프에는 그룹별 합계만 사용한다.
        self.rfm = result.reset_index()  # 고객 번호를 로컬 결과에만 보관한다.

        self.audit['rfm'] = {'reference_date': reference.date().isoformat(), 'frequency_unit': frequency, 'amount_unit': 'source price units; currency unverified', 'recency_median_days': recency_cut, 'frequency_median': frequency_cut, 'monetary_median': monetary_cut, 'segment_count': int(result['segment'].nunique()), 'score_ties': 'average percentile rank; equal values share scores'}  # 점수와 그룹 기준을 공개 가능한 형태로 기록한다.

        return self.rfm  # 고객별 결과를 반환하되 화면에는 집계만 표시한다.










    # ✅ [save_processed] 고객 그룹별 요약
    def segment_summary(self):  # 고객 번호가 없는 그룹별 요약을 만든다.
        summary = self.rfm.groupby('segment').agg(customers=('segment', 'size'), mean_recency=('recency', 'mean'), mean_frequency=('frequency', 'mean'), mean_monetary=('monetary', 'mean'), total_monetary=('monetary', 'sum'))  # 고객 컬럼 이름이 달라도 그룹의 규모와 특징을 계산한다.
        summary['customer_share'] = summary['customers'] / summary['customers'].sum()  # 고객 구성 비중을 계산한다.
        summary['monetary_share'] = summary['total_monetary'] / summary['total_monetary'].sum() if summary['total_monetary'].sum() else 0.0  # 금액 합계 비중의 분모를 명확히 한다.
        return summary.reindex([name for name in SEGMENTS if name in summary.index])  # 차트와 표의 순서를 일치시킨다.


    # ✅ [save_processed] 상품 특성
    def product_features(self):  # 상관관계는 거래 반복으로 상품이 과도하게 가중되지 않게 상품 단위로 계산한다.
        features = self.df.drop_duplicates('article_id').set_index('article_id')[['product_name_length', 'description_length', 'image_mean', 'image_std']]  # 상품 고유 특성은 한 번만 선택한다.
        features['mean_purchase_price'] = self.df.groupby('article_id')['price'].mean()  # 상품의 표본 내 평균 구매 가격을 계산한다.
        return features  # 상품당 한 행인 분석 표를 반환한다.


    # ✅ [save_processed] 상관관계와 산점도 데이터
    def correlations(self):  # 해석할 두 쌍 이상의 상관계수와 분석 대상 수를 계산한다.
        frame = self.product_features()  # 상품 단위 표를 선택한다.
        pairs = [('mean_purchase_price', 'product_name_length'), ('mean_purchase_price', 'image_mean'), ('image_mean', 'image_std')]  # 상품명과 이미지의 관계를 각각 살펴본다.
        records = []  # 두 변수별 결과를 모은다.
        for left, right in pairs:  # 변수 쌍별로 공통 관측치만 선택한다.
            subset = frame[[left, right]].dropna()  # 이미지 없는 상품을 0으로 채우지 않는다.
            valid = len(subset) >= 3 and subset[left].nunique() > 1 and subset[right].nunique() > 1  # 상관계수를 계산할 수 있는지 확인한다.
            coefficient = float(subset[left].corr(subset[right])) if valid else None  # 근거 없는 상관계수는 만들지 않는다.
            records.append({'left': left, 'right': right, 'n_products': len(subset), 'pearson_r': coefficient})  # 계수와 분모를 함께 기록한다.
        return pd.DataFrame(records)  # 보고서와 노트북에서 같은 계산을 사용한다.


    # ✅ [save_processed] 상관관계 히트맵의 칸별 상품 수
    def correlation_counts(self):  # 히트맵의 각 칸에 실제로 쓰인 상품 수를 계산한다.
        valid = self.product_features().notna().astype(int)  # 상품별로 특성이 있으면 1로 표시한다.
        return valid.T @ valid  # 두 특성이 동시에 있는 상품 수를 모든 변수 쌍에 대해 배열 연산으로 계산한다.


    # ✅ [save_processed] 월별 구매 금액
    def monthly_summary(self):  # 관측 기간의 월별 구매 금액을 모은다.
        grouped = self.df.set_index('order_date').resample('MS').agg(amount=('amount', 'sum'), purchase_rows=('amount', 'size'))  # 각 월의 시작일을 기준으로 합계와 구매 행 수를 계산한다.
        grouped.index.name = 'month'  # 날짜 축 이름을 명확히 한다.
        return grouped  # 첫 달과 마지막 달의 부분 기간 여부는 보고서에 함께 설명한다.


    # ✅ [save_processed] 주요 수치의 평균·중앙값·표준편차·사분위수
    def summary_statistics(self):  # 주요 수치의 평균·중앙값·표준편차·사분위수를 계산한다.
        return self.df[['price', 'product_name_length', 'description_length', 'image_mean', 'image_std']].describe().T  # 이미지 특성의 거래 행 수와 상품 수는 구분한다.


    # 행이 너무 많아서 미리보기용으로 위에서 몇 개만 보기 위한 util 함수
    def safe_preview(self, count=5):  # 공개 노트북에서 고객별 거래를 출력하지 않는 미리보기를 만든다.
        return self.df[['product_group_name', 'prod_name', 'product_name_length']].drop_duplicates().head(count)  # 상품 정보만 제한된 행 수로 보여 준다.

    # 데이터의 전체적인 구조 파악용 
    def schema_info(self):  # 값 대신 자료형과 비어 있지 않은 개수를 확인한다.
        buffer = io.StringIO()  # 표 구조 설명을 받을 공간을 만든다.
        self.df.info(buf=buffer)  # 과제의 info 함수를 사용한다.
        return buffer.getvalue()  # 고객 식별자 값은 포함하지 않는다.


    # ✅ Main 실행 함수 - 전체 필수 분석을 실행
    def run(self, min_images=100, iqr_factor=1.5, reference_date=None):  # 전체 필수 분석을 재현 가능한 순서로 실행한다.
        self.load_data()  # 거래와 상품을 연결한다.
        self.add_text_features()  # 실제 결측치를 유지하며 글 길이 특성을 만든다.
        self.handle_missing_values()  # 상품 단위 그룹 중앙값으로 설명 길이를 대치한다.
        self.detect_outliers(threshold=iqr_factor)  # 원본 가격은 보존하며 이상치 표시와 비교용 사본을 만든다.
        self.add_image_features(min_images=min_images)  # 실제 이미지를 읽고 배열 통계를 연결한다.
        self.calculate_rfm(reference_date=reference_date)  # 원래 구매 금액과 전체 기록으로 고객을 분석한다.
        return self  # 결과를 가진 분석 도구를 반환한다.


    # ✅ 재사용할 분석 결과를 Git 제외 데이터 폴더에 저장
    def save_processed(self, output_dir):  # 재사용할 분석 결과를 Git 제외 데이터 폴더에 저장한다.
        output = Path(output_dir)  # 사용자가 지정한 출력 위치를 다룬다.
        output.mkdir(parents=True, exist_ok=True)  # 출력 폴더가 없으면 만든다.
        self.df.to_csv(output / 'transactions_enriched.csv', index=False)  # 고객별 표는 공개하지 않는 로컬 결과로 저장한다.
        self.rfm.to_csv(output / 'customer_rfm.csv', index=False)  # 실제 고객 번호가 있는 결과도 로컬 데이터 폴더에 둔다.
        self.product_features().to_csv(output / 'product_features.csv')  # 이미지와 글의 상품 단위 특성을 저장한다.
        self.segment_summary().to_csv(output / 'segment_summary.csv')  # 공개 설명에 사용할 그룹 집계를 저장한다.
        self.monthly_summary().to_csv(output / 'monthly_summary.csv')  # 시계열 집계를 저장한다.
        self.correlations().to_csv(output / 'correlations.csv', index=False)  # 변수 쌍의 계수와 표본 크기를 저장한다.
        self.correlation_counts().to_csv(output / 'correlation_counts.csv')  # 히트맵의 모든 칸에 쓰인 분모를 별도로 저장한다.
        self.summary_statistics().to_csv(output / 'statistics.csv')  # 요약 통계를 저장한다.
        (output / 'analysis_summary.json').write_text(json.dumps(self.audit, ensure_ascii=False, indent=4, allow_nan=False) + '\n')  # 기준·출처 비교값·검사 집계만 기록한다.
