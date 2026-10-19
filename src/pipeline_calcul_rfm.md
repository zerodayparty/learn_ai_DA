# 🟩 RFM 관련 원리에 대한 분석  


```python
# ✅ RFM 고객 특성 계산  
    # 이 함수의 목표: 구매 기록은 한 고객이 여러 행에 흩어져 있으므로,  
    # 고객마다 한 행짜리 요약표를 만들고 구매 행동이 비슷한 고객끼리 나눈다.  
    #  
    # RFM은 세 가지 영어 단어의 첫 글자를 붙인 이름이다.  
    # R = Recency: 마지막 구매로부터 며칠 지났는가? → 작을수록 최근 구매다.  
    # F = Frequency: 얼마나 자주 구매했는가? → 클수록 구매 기록이 많다.  
    # M = Monetary: 구매 금액을 모두 더하면 얼마인가? → 클수록 금액 합계가 크다.  
    #  
    # 이 함수에는 서로 다른 두 작업이 들어 있다.  
    # 1. r_score / f_score / m_score: 각 특성을 1~4점으로 표현한다.  
    # 2. segment: R·F·M의 원래 값과 중앙값을 비교해 네 고객 그룹으로 나눈다.  
        # 주의: 여기서는 1~4점 점수를 이용해서 네 그룹을 만드는 것이 아니다.  
        # 점수 열은 요약용이고, 실제 그룹 조건은 아래의 recent와 valuable이다.  

    # 입력: self.df에 들어 있는 현재 표본의 전체 관측 기간 구매 기록.  
    # 전체 관측 기간이라는 말은 이 표본 안의 모든 기간이라는 뜻이다.  
    # H&M 전체 고객이나 이 고객들의 평생 구매 이력을 확보했다는 뜻은 아니다.  
    # 출력: 고객마다 마지막 구매일, R·F·M, 세 점수, 그룹 이름을 넣은 표.  
    #  
    # 함수 인자 읽는 법:  
    # self: 현재 DataAnalyzer 객체이며, self.df 같은 분석 자료를 갖고 있다.  
    # customer_col: 고객 번호가 들어 있는 열 이름. 기본값은 'customer_id'.  
    # date_col: 날짜가 들어 있는 열 이름. 기본값은 'order_date'.  
    # amount_col: 금액이 들어 있는 열 이름. 기본값은 'amount'.  
    # reference_date: R을 계산할 기준일. None이면 표본의 마지막 구매일을 쓴다.  
    # frequency: F를 구매 행 수로 셀지, 서로 다른 구매일 수로 셀지 정한다.  
    # 열 이름을 인자로 받으므로 같은 계산을 다른 이름의 표에도 적용할 수 있다.  
    def calculate_rfm(self, customer_col='customer_id', date_col='order_date', amount_col='amount', reference_date=None, frequency='purchase_rows'):  # 전체 구매 이력으로 고객 특성을 계산한다.  

        # 🟢 1. 구매 빈도(F)의 단위를 먼저 정한다.  
        # 'purchase_rows': 구매 기록의 행 수. 같은 날 세 행이 있으면 3이다.  
        # 'purchase_days': 구매한 날짜의 종류 수. 같은 날 세 행이면 1이다.  
        # 예: 9월 20일에 두 행, 9월 21일에 한 행 → purchase_rows=3, purchase_days=2.  
        # 이 데이터에는 주문 번호가 없으므로 행 수를 정확한 주문 횟수라고 부르면 안 된다.  
        # 함수 기본값은 purchase_rows이므로 따로 지정하지 않으면 행 수가 F가 된다.  
        # not in은 '허용된 두 문자열 중 어느 것도 아닌가?'를 확인하는 파이썬 표현이다.  
        if frequency not in {'purchase_rows', 'purchase_days'}:  # 주문 수로 잘못 부르지 않게 허용하는 단위를 정한다.  

        # ValueError는 '인자로 받은 값이 허용 범위와 맞지 않는다'는 오류다.  
        # 예를 들어 frequency='orders'를 넣으면 조용히 추측해서 계산하지 않고 멈춘다.  
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


        # ============================================================================  
        # 🟢 🔥🔥🔥🔥🔥 8. 네 그룹으로 나누기 위한 기준값을 별도로 구한다.  
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
        #  
        # 조건                           → 붙이는 그룹 이름  
        # recent & valuable              → Recent buyers / Frequent & high spending  
        # recent & ~valuable             → Recent buyers / Less frequent or lower spending  
        # ~recent & valuable             → No recent purchase / Frequent & high spending  
        # 위 세 조건에 해당하지 않음      → No recent purchase / Less frequent or lower spending  
        # 마지막 경우는 ~recent & ~valuable과 같다. 네 조건은 서로 겹치지 않는다.  
        #  
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

        # self.audit는 계산에 쓴 기준과 결과 규모를 기록하는 파이썬 딕셔너리다.  
        # 여기에 숫자를 기록해 두면 그래프 설명이 실제 계산 기준과 어긋나는 것을 줄일 수 있다.  
        # reference_date: 계산 기준일. .date().isoformat()은 날짜를 YYYY-MM-DD 문자열로 만든다.  
        # frequency_unit: F가 구매 행 수인지 구매일 수인지 기록한다.  
        # amount_unit: 원본 가격 단위이며 통화를 확인하지 않았다는 정보를 남긴다.  
        # recency_median_days / frequency_median / monetary_median: 실제로 쓴 세 중앙값.  
        # segment_count: .nunique()로 실제 고객이 존재하는 그룹 수를 센다.  
        # 네 종류를 정의해도 어떤 입력에서는 한 그룹이 비어 실제 그룹 수가 4보다 적을 수 있다.  
        # score_ties: 동점에 평균 순위를 적용하고 같은 값에 같은 점수를 준다는 계산 규칙이다.  
        # 이 기록에는 고객 번호나 고객별 구매 내역을 넣지 않는다.  
        self.audit['rfm'] = {'reference_date': reference.date().isoformat(), 'frequency_unit': frequency, 'amount_unit': 'source price units; currency unverified', 'recency_median_days': recency_cut, 'frequency_median': frequency_cut, 'monetary_median': monetary_cut, 'segment_count': int(result['segment'].nunique()), 'score_ties': 'average percentile rank; equal values share scores'}  # 점수와 그룹 기준을 공개 가능한 형태로 기록한다.  

        # 반환한 표는 이후 그룹별 인원 집계, 그래프, 결과 설명의 공통 재료가 된다.  
        # return 자체는 화면 출력이나 파일 저장이 아니다. 호출한 쪽에 표를 돌려준다.  
        # 실제 저장은 별도의 save_processed()에서, 공개용 집계는 segment_summary()에서 한다.  
        return self.rfm  # 고객별 결과를 반환하되 화면에는 집계만 표시한다.  
```