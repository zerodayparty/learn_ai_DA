import math  # 빈 상관계수를 숫자처럼 표시하지 않도록 확인한다.
import pandas as pd  # 집계 표를 읽기 쉬운 형태로 바꾼다.


MISSING_VALUE_RATIONALE = (  # 보고서와 노트북에서 같은 대치 선택 근거를 사용한다.
    '상품 종류마다 설명 길이가 다를 수 있어 전체 평균 대신 같은 상품군의 대표값을 사용했다. '  # 그룹으로 나눈 이유를 설명한다.
    '중앙값은 매우 긴 설명 몇 개의 영향을 평균보다 덜 받으므로 이번 기본 전략으로 골랐다. '  # 중앙값 선택은 검증된 최적 전략이라고 주장하지 않는다.
    '상품당 한 번 계산하고, 해당 상품군 전체가 비었다면 전체 상품의 중앙값으로 보완한다. '  # 실제 대치 순서와 계산 단위를 밝힌다.
    '대치는 같은 값이 반복돼 그룹 안의 퍼짐을 줄이거나, 결측 원인이 편향됐을 때 그룹 차이·상관관계를 왜곡할 수 있다. '  # 대치 결과를 실제 관측값처럼 읽지 않게 한다.
    '그래서 원래 결측 여부를 남겼으며, 평균 대치와 비교해 중앙값이 더 우수하다고 검증한 것은 아니다.'  # 선택 근거와 실험 결과를 구분한다.
)  # 대치 설명을 하나의 문자열로 묶는다.

OUTLIER_RATIONALE = (  # 보고서와 노트북에서 같은 이상치 탐지 목적을 사용한다.
    'IQR 탐지의 목적은 극단적인 가격이 평균과 분포에 주는 영향을 살펴볼 구매를 찾는 것이다. '  # 경계 계산 뒤에 할 일을 설명한다.
    '정규분포를 필수로 가정하지 않지만 비대칭·긴 꼬리 분포에서는 정상 고가 구매도 표시될 수 있다. '  # 탐지와 오류 확정을 구분한다.
    '원본과 경계값에 맞춘 사본의 박스플롯을 비교하며, 구매 행은 삭제하지 않는다. '  # 비교용 처리의 범위를 밝힌다.
    '사본의 큰 가격을 줄였다는 이유로 실제 고객 금액까지 줄이지 않도록 RFM은 원래 가격을 사용한다.'  # 고객 분석에 쓰는 값을 명확히 한다.
)  # 이상치 설명을 하나의 문자열로 묶는다.


# 추가 라이브러리 없이 집계 표를 Markdown으로 만든다.
def markdown_table(frame):  

    has_row_labels = frame.index.name is not None or not frame.index.equals(pd.RangeIndex(len(frame)))  # 이름이 없어도 실제 행 이름표가 있는지 확인한다.
    table = frame.reset_index() if has_row_labels else frame.copy()  # 실제 행 이름은 남기고 기본 행 번호는 생략한다.
    
    def format_value(value):  # 숫자와 결측치 표시를 일관되게 한다.
        if pd.isna(value):  # 계산하지 못한 값을 0으로 표현하지 않는다.
            return '미계산'  # 분석 대상 부족과 실제 0을 구분한다.
        if isinstance(value, float):  # 실수는 필요한 자릿수만 표시한다.
            return f'{value:,.4f}'  # 원본 가격 단위의 작은 값을 읽을 수 있게 한다.
        return str(value).replace('|', '/')  # 표 구분 기호가 내용으로 들어가도 표가 깨지지 않게 한다.
    
    header = '| ' + ' | '.join(map(str, table.columns)) + ' |'  # 표 머리글을 만든다.
    
    separator = '| ' + ' | '.join(['---'] * len(table.columns)) + ' |'  # Markdown 표 구분 행을 만든다.
    
    rows = ['| ' + ' | '.join(format_value(value) for value in row) + ' |' for row in table.itertuples(index=False, name=None)]  # 고객 행이 아닌 집계 값만 표로 정리한다.
    
    return '\n'.join([header, separator, *rows])  # README와 분석 문서에서 같은 형식을 사용한다.


def statistics_interpretations(analyzer):  # 다섯 수치 특성의 근거와 해석을 같은 실행 결과로 만든다.
    statistics = analyzer.summary_statistics()  # 반올림 전 요약값을 사용한다.
    descriptions = [  # 각 열의 단위와 해석상 주의점을 정한다.
        ('price', '구매가격', '원본 가격 단위', '평균과 중앙값의 차이는 큰 가격의 영향을 살펴볼 단서다. 통화·할인 정보를 확인하기 전 비싸다거나 이익이 높다고 단정하지 않는다.'),  # 구매금액의 해석 범위를 제한한다.
        ('product_name_length', '상품명 길이', '글자', '25~75% 지점의 길이로 구매에 연결된 상품명의 대표 범위를 읽는다. 이름 길이가 가격과 관련되는지는 상품 단위 상관분석으로 따로 확인한다.'),  # 길이와 가격을 바로 인과관계로 연결하지 않는다.
        ('description_length', '설명 길이', '글자', '상품군 중앙값으로 채운 설명 길이도 포함한다. 이 퍼짐은 원래 관측값만의 분포가 아니므로 대치 전 분포와 같다고 해석하지 않는다.'),  # 대치가 섞인 통계임을 밝힌다.
        ('image_mean', '사진 색상 평균', '0~1 색상 값', '25~75% 지점으로 사진의 평균 색상 수준이 모인 범위를 읽는다. 배경·촬영 방식의 영향도 있어 상품 자체의 성질이나 전체 상품의 특징으로 단정하지 않는다.'),  # 사진 색상을 품질처럼 해석하지 않는다.
        ('image_std', '사진 안 색상 퍼짐', '0~1 색상 값', '이 피처가 큰 사진은 사진 안 색상 숫자의 차이가 큰 편이다. 이 행의 표준편차는 사진별 퍼짐 값들이 구매 행들 사이에서 다시 얼마나 다른지를 나타낸다.'),  # 사진 내부 퍼짐과 피처 간 퍼짐을 구분한다.
    ]  # 통계표와 같은 다섯 변수를 설명한다.
    paragraphs = []  # 노트북과 글 보고서에서 함께 사용할 문장을 모은다.
    for column, label, unit, implication in descriptions:  # 변수마다 수치와 시사점을 연결한다.
        row = statistics.loc[column]  # 해당 변수의 통계 한 행을 고른다.
        count = int(row['count'])  # 실제 계산에 사용한 구매 행 수를 센다.
        if count == 0:  # 사진 등이 전혀 없어 통계를 계산할 수 없는 경우를 구분한다.
            paragraphs.append(f'- **{label} (`{column}`)**: 관측한 구매 행이 0개라 통계와 해석을 보류한다. 누락을 실제 숫자 0으로 대치하지 않았다.')  # 빈 자료로 결론을 만들지 않는다.
            continue  # 값이 없는 변수의 평균과 사분위수를 출력하지 않는다.
        evidence = f"구매 {count:,}행에서 평균 {row['mean']:.6f}, 중앙값 {row['50%']:.6f}, 표준편차 {row['std']:.6f}, Q1 {row['25%']:.6f}, Q3 {row['75%']:.6f} ({unit})다."  # 주요 통계 다섯 개를 실제 계산값으로 적는다.
        scope = '사진이 있는 구매 행 기준이며 같은 사진이 반복 구매에 여러 번 포함된다. 서로 다른 사진 수나 전체 구매 분포와 구분한다.' if column.startswith('image_') else '구매 행 기준이므로 많이 팔린 상품은 반복 포함된다. 상품마다 한 번 계산하는 상관분석과 구분한다.'  # 거래 가중 통계와 상품 단위 통계를 구분한다.
        paragraphs.append(f'- **{label} (`{column}`)**: {evidence} {implication} {scope}')  # 수치·해석·대상 범위를 한 문단에 묶는다.
    return paragraphs  # 보고서와 노트북이 같은 해석을 표시하게 한다.



# 실행한 결과에서만 근거를 가져와 제안을 만든다.
def business_insights(analyzer):  

    groups = analyzer.segment_summary()  # 고객별 개인정보가 없는 집계를 선택한다.

    recent_value = groups.loc['Recent high value']  # 최근·고빈도·고금액 고객의 실제 수치를 읽는다.

    less_recent = groups.loc['Less recent high value']  # 상대적으로 오래 방문하지 않은 고가치 고객을 읽는다.

    recent_other = groups.loc['Recent other']  # 그 외 최근 구매 고객의 실제 수치를 읽는다.

    return [  # 세 인사이트를 같은 근거·실행·검증 구조로 만든다.
        {'title': '최근 고빈도·고금액 고객의 관계 유지', 'evidence': f"Recent high value {int(recent_value['customers'])}명은 고객의 {recent_value['customer_share']:.1%}, 표본 구매 금액 합계의 {recent_value['monetary_share']:.1%}다.", 'action': '이 그룹에 구매 상품군과 연관된 추천을 소규모 대조 실험으로 제공한다. 목표는 재구매 유지이며 개선율은 아직 측정하지 않았다.', 'validation': '통제군과 비교한 재구매율·순이익, 반품·할인·동의 정보를 추가로 확인해야 한다. 높은 금액만으로 추천의 효과가 입증되지는 않는다.'},  # 할인 효과나 이익을 가정하지 않는다.
        {'title': '상대적으로 오래 미구매한 고가치 고객의 재방문 검증', 'evidence': f"Less recent high value {int(less_recent['customers'])}명의 평균 미구매 간격은 {less_recent['mean_recency']:.1f}일이고 표본 금액 비중은 {less_recent['monetary_share']:.1%}다.", 'action': '이 그룹을 대상으로 재방문 안내와 미제공 대조군을 비교하는 실험을 설계한다. 목표는 재방문율 개선이며 실제 개선율은 아직 측정하지 않았다. 과거 구매일 기준 분류이며 현재 실제 이탈 고객이라고 단정하지 않는다.', 'validation': '관측 종료 뒤 구매 기록과 수신 동의, 재방문 이유가 필요하다. 관측 기간 종료 때문에 재방문을 못 본 것일 수도 있다.'},  # 관측 종료와 실제 이탈을 구분한다.
        {'title': '그 외 최근 구매 고객의 후속 구매 기회', 'evidence': f"Recent other {int(recent_other['customers'])}명의 평균 구매 빈도는 {recent_other['mean_frequency']:.2f}행, 평균 금액 합계는 {recent_other['mean_monetary']:.4f} 원본 가격 단위다.", 'action': '이 그룹에 상품 사용 정보와 관련 상품 추천을 제공하는 실험을 설계하고 다음 구매일까지의 기간을 비교한다. 목표는 후속 구매까지의 기간 단축이며 실제 효과는 아직 측정하지 않았다. 신규 회원이라는 근거가 없으므로 신규 고객이라고 부르지 않는다.', 'validation': '가입일·반품·배송 만족도와 후속 구매 관측 기간이 필요하다. 단순한 계절 구매 고객이라면 추천 효과가 없을 수 있다.'},  # 없는 가입일과 구매량을 만들지 않는다.
    ]  # 실제 실행이나 고객 메시지 전송은 하지 않는다.



# 실제 결과에 근거한 한국어 분석 설명을 만든다.
def analysis_markdown(analyzer):  
    
    audit = analyzer.audit  # 같은 실행의 처리 기준을 읽는다.

    images = audit['images']  # 실제 디코딩과 거래 연결 범위를 읽는다.

    groups = analyzer.segment_summary()  # 개인정보 없는 집계 표를 만든다.

    parts = ['# 🟩 H&M 고객 표본 분석 결과', '## 🟢 분석 범위와 해석 기준', f"고객 {audit['customers']:,}명, 거래 {audit['rows']:,}행, 상품 {audit['products']:,}개를 분석했다. 기간은 {audit['date_min']}~{audit['date_max']}다. 전체 H&M 고객이나 현재 영업 상태의 추정 결과가 아니다.", '입력은 data/sample/transactions.csv, articles.csv와 data/raw/images의 실제 이미지다. 출처는 [H&M 대회](https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data)이며, 데이터 이용은 대회 규칙을 따른다.', '한 행은 구매 기록이다. 반복 행은 보존했다. Frequency는 주문 수가 아닌 구매 행 수, Monetary는 원본 price 합계다. 가격 통화 단위는 확인되지 않았으므로 원화 매출이나 이익으로 해석하지 않는다.', f"RFM 기준일은 {audit['rfm']['reference_date']}다. 최근 구매 기준은 고객 미구매 간격 중앙값 {audit['rfm']['recency_median_days']:.1f}일 이하이고, 고가치 기준은 구매 빈도 {audit['rfm']['frequency_median']:.1f}행 이상과 금액 {audit['rfm']['monetary_median']:.4f} 이상을 동시에 만족하는 것이다.", '<br><br>', '## 🟢 결측치와 이상치 처리', MISSING_VALUE_RATIONALE, OUTLIER_RATIONALE, f"상품 설명이 없는 {audit['imputation']['missing_products']}개 상품의 설명 길이를 같은 상품군 중앙값으로 대치했다. 상품당 한 번 계산하므로 많이 팔린 상품에 대치 통계가 치우치지 않는다. 영향을 받은 거래는 {audit['imputation']['filled_transaction_rows']}행이다. 원래 설명 문장을 만들어 넣은 것은 아니다.", f"가격 IQR 범위 밖은 {audit['outliers']['count']}행이다. Q1={audit['outliers']['q1']:.6f}, Q3={audit['outliers']['q3']:.6f}, 배율={audit['outliers']['factor']:.2f}를 사용했다. 경계 대치 사본으로 분포를 비교하고 RFM에는 원래 가격을 썼다.", '<br><br>', '## 🟢 이미지와 텍스트 특성', f"실제 이미지 {images['decoded_products']}개를 디코딩했고 {images['covered_transaction_rows']}개 거래 행({images['coverage_fraction']:.2%})에 연결했다. 이미지가 없는 거래는 삭제하지 않았다. 이미지 평균·표준편차는 RGB 픽셀을 0~1로 맞춘 배열에서 계산했다. 상품명 문자 수·단어 수도 추가했다.", '이미지는 상품군을 번갈아 선택한 일부이므로 전체 상품을 대표하지 않는다. 이미지 상관관계의 분모는 사진이 있는 상품 수다. 설명 길이는 대치한 값이 포함되므로 원래 관측한 설명 길이와 구분해야 한다.', '<br><br>', '## 🟢 주요 요약 통계', markdown_table(analyzer.summary_statistics().rename_axis('feature').round(6)), 'price 통계는 구매 행 단위다. 이미지 통계의 count는 해당 사진이 연결된 구매 행 수로, 서로 다른 사진 수와 다르다. 평균·중앙값·표준편차·25%와 75%를 함께 비교해야 분포의 치우침을 읽을 수 있다.', *statistics_interpretations(analyzer), '<br><br>', '## 🟢 상품 단위 상관관계']  # 근거와 한계를 각 결과 옆에 둔다.

    parts.append(markdown_table(analyzer.correlations()))  # 상관계수와 공통 상품 수를 함께 보여 준다.

    for row in analyzer.correlations().itertuples(index=False):  # 각 관계를 실제 계수로 해석한다.
        if row.pearson_r is not None and math.isfinite(row.pearson_r):  # 계산되지 않은 계수로 결론을 만들지 않는다.
            direction = '양의' if row.pearson_r >= 0 else '음의'  # 계수 부호를 해석에 반영한다.
            parts.append(f"- {row.left}와 {row.right}: 상품 {row.n_products:,}개에서 r={row.pearson_r:.4f}인 {direction} 관계다. 선형 관계의 크기는 |r|={abs(row.pearson_r):.4f}다. 이 특성 하나로 가격이나 구매를 설명할 수 있는지 판단하려면 추가 분석이 필요하며 인과 효과는 입증되지 않았다.")  # 수치 근거와 시사점을 함께 쓴다.

    parts.extend(['<br><br>', '## 🟢 RFM 그룹 집계', markdown_table(groups), '그룹은 최근 구매 여부와 빈도·금액 기준으로 나눈다. R·F·M 점수는 평균 백분위 순위로 계산해 같은 값에 같은 점수를 준다. 점수만으로 생애가치나 미래 구매를 예측하지 않는다.', '<br><br>', '## 🟢 비즈니스 인사이트'])  # 그룹 통계와 제안을 연결한다.

    for insight in business_insights(analyzer):  # 검증한 집계로 만든 세 제안을 기록한다.
        parts.extend([f"### 🟡 {insight['title']}", '- 근거: ' + insight['evidence'], '- 실행: ' + insight['action'], '- 검증: ' + insight['validation']])  # 근거·실행·반증 가능성을 분리한다.
    parts.extend(['<br><br>', '## 🟢 그래프와 재현', 'reports/figures에 가격 히스토그램·IQR 전후 박스플롯·고객 그룹 막대그래프·상관 히트맵·이미지 밝기 산점도·월별 합계 라인차트 여섯 종류를 저장했다. 첫 달과 마지막 달은 부분 관측 기간이므로 월별 증감을 계절성이나 성장으로 단정하지 않는다.', '노트북은 같은 분석 코드와 그림 함수를 사용한다. 고객별 표와 전처리 결과는 Git 제외 data/processed에만 보관하고 공개 문서와 노트북 출력에는 고객별 식별자·거래 행을 넣지 않는다.'])  # 재현 경로와 공개 범위를 기록한다.

    return '\n\n'.join(parts) + '\n'  # 문단 간격을 둔 Markdown을 반환한다.
