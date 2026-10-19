from pathlib import Path  # 차트 저장 위치를 다룬다.
from textwrap import fill  # 긴 그룹 이름과 설명을 줄바꿈한다.
import matplotlib.dates as mdates  # 날짜 축을 읽기 쉽게 표시한다.
import matplotlib.pyplot as plt  # 과제에서 허용한 그림 도구를 사용한다.
import pandas as pd  # 월별 날짜 눈금과 차트용 표를 다룬다.
import seaborn as sns  # 상관행렬 히트맵에 사용할 허용 도구를 가져온다.
from .pipeline import SEGMENTS  # 분석 표와 같은 고객 그룹 순서를 사용한다.


COLORS = dict(zip(SEGMENTS, ['#35678D', '#99B9CE', '#A06D22', '#DAC394']))  # 고객 그룹의 색을 모든 그림에서 고정한다.


def build_charts(analyzer, output_dir=None):  # 실제 분석 결과로 필수 그래프 여섯 종류를 만든다.
    sns.set_theme(style='whitegrid', font='DejaVu Sans', rc={'axes.titlesize': 13, 'axes.labelsize': 11, 'xtick.labelsize': 10, 'ytick.labelsize': 10, 'grid.alpha': 0.22})  # 공통 글꼴·크기·격자를 정한다.
    figures = {}  # 노트북 표시와 파일 저장에 같은 그림을 사용한다.
    context = f"H&M customer sample | {analyzer.audit['customers']:,} customers | {analyzer.audit['date_min']} to {analyzer.audit['date_max']}"  # 표본과 기간을 모든 차트에 붙인다.
    
    def frame(title, xlabel, ylabel, note):  # 같은 양식의 차트 틀을 만든다.
        figure, axis = plt.subplots(figsize=(9.5, 5.5))  # 라벨이 읽히는 그림 크기를 정한다.
        axis.set(title=title, xlabel=xlabel, ylabel=ylabel)  # 모든 그림에 제목과 축 이름을 붙인다.
        figure.subplots_adjust(left=0.13, right=0.96, top=0.88, bottom=0.22)  # 긴 설명과 축 눈금을 위한 여백을 확보한다.
        figure.text(0.02, 0.025, context + '\n' + fill(note, 115), fontsize=9, color='#475569')  # 단위·표본·한계를 그림과 함께 보관한다.
        return figure, axis  # 실제 데이터를 그릴 틀을 반환한다.
    
    figure, axis = frame('Purchase price distribution', 'Price (source units; currency unverified)', 'Purchase rows', f"All {len(analyzer.df):,} purchase rows; repeated purchases retained; no outlier rows removed.")  # 전체 가격 분포를 살펴본다.
    axis.hist(analyzer.df['price'], bins=40, color='#35678D', edgecolor='white', linewidth=0.5)  # 연속된 가격 구간별 거래 행 수를 그린다.
    axis.set_ylim(bottom=0)  # 구매 건수의 기준선을 0으로 둔다.
    
    # ✅ 01
    figures['01_price_histogram'] = figure  # 첫 번째 그래프를 등록한다.
    figure, axis = frame('Price before and after IQR clipping', 'Comparison policy', 'Price (source units)', f"Same {len(analyzer.df):,} rows in both boxes. Clipped values are for comparison; RFM uses original prices.")  # 원본과 경계 대치 사본을 비교한다.
    boxes = axis.boxplot([analyzer.df['price'], analyzer.df['price_clipped']], tick_labels=['Original', 'Clipped copy'], patch_artist=True, widths=0.45)  # 행 삭제 없이 전후 분포를 비교한다.
    for box, color in zip(boxes['boxes'], ['#35678D', '#C8A350']):  # 두 정책을 색으로 구분한다.
        box.set_facecolor(color)  # 상자의 채우기 색을 정한다.
    
    # ✅ 02
    figures['02_price_boxplot'] = figure  # 두 번째 그래프를 등록한다.
    segments = analyzer.segment_summary()  # 고객별 행 대신 그룹별 집계를 사용한다.
    rfm = analyzer.audit['rfm']  # 이번 실행에서 사용한 최근 구매·빈도·금액 기준을 읽는다.
    frequency_unit = 'purchase rows' if rfm['frequency_unit'] == 'purchase_rows' else 'purchase days'  # 빈도 계산의 실제 단위를 표시한다.
    note = f"Recent: last purchase within {rfm['recency_median_days']:g} days as of {rfm['reference_date']}. Frequent: at least {rfm['frequency_median']:g} {frequency_unit}; high spending: total original price at least {rfm['monetary_median']:.6f} source units. Less frequent or lower spending: below at least one of these purchase thresholds."  # 라벨을 읽는 데 필요한 기준을 공개한다.
    figure, axis = frame('Customer groups by last purchase and buying activity', 'Number of customers', 'Customer group', note)  # 최근 여부와 구매 행동을 드러내는 제목·축을 사용한다.
    figure.set_size_inches(11.5, 6.5)  # 두 줄 라벨과 기준 설명이 들어갈 공간을 확보한다.
    labels = [name.replace(' / ', '\n') for name in segments.index]  # 최근 구매 여부와 구매 규모를 두 줄로 나눠 표시한다.
    bars = axis.barh(labels, segments['customers'], color=[COLORS[name] for name in segments.index])  # 네 그룹의 고객 수를 그린다.
    axis.bar_label(bars, padding=5, fmt='%.0f')  # 색상만으로 비교하지 않도록 정확한 수를 표시한다.
    axis.set_xlim(0, segments['customers'].max() * 1.22)  # 막대는 0에서 시작하고 숫자 표시 여유를 둔다.
    axis.invert_yaxis()  # 요약 표와 같은 순서로 보여 준다.
    figure.subplots_adjust(left=0.36, bottom=0.25)  # 라벨을 줄이거나 자르지 않고 왼쪽과 아래 공간을 확보한다.
    
    # ✅ 03
    figures['03_segment_bar'] = figure  # 세 번째 그래프를 등록한다.
    products = analyzer.product_features()  # 상관관계는 상품당 한 행으로 계산한다.
    columns = ['mean_purchase_price', 'product_name_length', 'description_length', 'image_mean', 'image_std']  # 해석할 숫자 특성만 고른다.
    matrix = products[columns].corr(min_periods=3)  # 변수 쌍별 공통 관측치로 피어슨 계수를 계산한다.
    names = ['Mean price', 'Name length', 'Desc. length', 'Image mean', 'Image std']  # 차트 안에서 읽을 수 있는 짧은 이름을 정한다.
    matrix.index, matrix.columns = names, names  # 두 축의 특성 이름을 맞춘다.
    figure, axis = frame('Product feature correlations', 'Product feature', 'Product feature', f"Up to {len(products):,} unique products; image pairs use decoded products only. Pairwise counts: correlation_counts.csv. Association is not causation.")  # 각 관계의 분모가 다를 수 있음을 밝힌다.
    sns.heatmap(matrix, ax=axis, annot=True, fmt='.2f', cmap='vlag', center=0, vmin=-1, vmax=1, square=False, cbar_kws={'label': 'Pearson r'})  # 양·음 관계에 같은 계수 범위를 사용한다.
    axis.tick_params(axis='x', rotation=0)  # 가로 라벨을 수평으로 읽게 한다.
    axis.tick_params(axis='y', rotation=0)  # 세로 라벨도 수평으로 유지한다.
    figure.subplots_adjust(left=0.18, bottom=0.24)  # 축 이름이 잘리지 않게 여백을 확보한다.
    
    # ✅ 04
    figures['04_correlation_heatmap'] = figure  # 네 번째 그래프를 등록한다.
    visible = products[['mean_purchase_price', 'image_mean']].dropna()  # 실제 이미지가 있는 상품만 산점도에 넣는다.
    figure, axis = frame('Image brightness and observed purchase price', 'Mean purchase price (source units)', 'Mean RGB intensity (0-1)', f"One point per product; n={len(visible):,} image-covered products. Selected images are not a representative sample of the full catalog.")  # 관측 단위와 선택 편향을 밝힌다.
    axis.scatter(visible['mean_purchase_price'], visible['image_mean'], color='#35678D', alpha=0.7, s=34, edgecolor='white', linewidth=0.5)  # 한 상품을 점 하나로 표현한다.
    axis.set_ylim(0, 1)  # 이미지 밝기의 실제 정규화 범위를 유지한다.
    
    # ✅ 05
    figures['05_image_price_scatter'] = figure  # 다섯 번째 그래프를 등록한다.
    monthly = analyzer.monthly_summary()  # 월별 합계와 구매 행 수를 읽는다.
    figure, axis = frame('Monthly purchase amount in the customer sample', 'Month', 'Sum of original prices (source units)', 'The first and last calendar months are partial observation months. This is a customer sample, not total company revenue.')  # 부분 기간과 모집단을 설명한다.
    axis.plot(monthly.index, monthly['amount'], color='#35678D', marker='o', markersize=4, linewidth=1.8)  # 실제 관측 월을 순서대로 연결한다.
    ticks = sorted(set([monthly.index.min(), monthly.index.max(), *pd.date_range(monthly.index.min(), monthly.index.max(), freq='6MS')]))  # 첫 달과 마지막 달을 반드시 표시한다.
    axis.set_xticks(ticks)  # 읽기 쉬운 간격으로 날짜 눈금을 배치한다.
    axis.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))  # 날짜의 표시 형식을 통일한다.
    axis.set_ylim(bottom=0)  # 금액 합계의 기준선을 0으로 둔다.
    
    # ✅ 06
    figures['06_monthly_line'] = figure  # 여섯 번째 그래프를 등록한다.
    if output_dir is not None:  # 파일 저장을 요청한 경우만 출력 폴더에 쓴다.
        output = Path(output_dir)  # 그래프 폴더를 선택한다.
        output.mkdir(parents=True, exist_ok=True)  # 그래프 저장 폴더를 만든다.
        for name, figure in figures.items():  # 같은 그림을 노트북과 PNG에서 재사용한다.
            figure.savefig(output / (name + '.png'), dpi=150, facecolor='white')  # 외부 폰트나 네트워크 없이 차트를 저장한다.
    
    
    return figures  # 노트북은 그림을 각각의 셀에서 표시할 수 있다.
