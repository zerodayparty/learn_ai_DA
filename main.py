import argparse  # 실행 시 분석 기준을 선택하는 도구를 가져온다.
import os  # 화면 없는 환경에서도 차트를 저장할 수 있게 한다.
from pathlib import Path  # 실행 위치와 관계없이 프로젝트를 찾는다.
os.environ.setdefault('MPLBACKEND', 'Agg')  # 터미널에서는 GUI 창 대신 그림 파일을 만든다.
from src.pipeline import DataAnalyzer  # 데이터 분석 클래스를 가져온다.
from src.charts import build_charts  # 같은 분석 결과에서 여섯 그래프를 만드는 도구를 가져온다.
from src.reporting import analysis_markdown  # 근거 있는 한국어 결과 설명을 만드는 도구를 가져온다.
import matplotlib.pyplot as plt  # 파일 저장을 마친 그림 메모리를 정리한다.


def main():  # 전체 분석 실행의 시작점을 정의한다.
    root = Path(__file__).resolve().parent  # 사용자 개인 경로를 출력하지 않고 프로젝트를 찾는다.
    parser = argparse.ArgumentParser(description='H&M 표본의 전처리·통계·RFM·차트 분석')  # 명령 도움말을 만든다.
    parser.add_argument('--sample-dir', type=Path, default=root / 'data/sample', help='거래·상품 표본 폴더')  # 입력 표본 위치를 선택할 수 있게 한다.
    parser.add_argument('--image-dir', type=Path, default=root / 'data/raw/images', help='상품 이미지 폴더')  # 이미지 위치를 선택할 수 있게 한다.
    parser.add_argument('--min-images', type=int, default=100, help='실제 디코딩할 최소 이미지 수')  # 마커 검사가 아닌 실제 이미지 해석 규모를 정한다.
    parser.add_argument('--iqr-factor', type=float, default=1.5, help='IQR 이상치 범위 배율')  # 이상치 기준을 실험할 수 있게 한다.
    parser.add_argument('--reference-date', default=None, help='RFM 기준일 YYYY-MM-DD, 기본은 마지막 거래일')  # 최근 구매 간격의 기준일을 명시할 수 있게 한다.
    args = parser.parse_args()  # 사용자 실행 옵션을 읽는다.
    print('1/4 표본 연결·결측치·이상치·실제 이미지·RFM 계산', flush=True)  # 지금 하는 작업을 알린다.
    analyzer = DataAnalyzer(args.sample_dir, args.image_dir).run(min_images=args.min_images, iqr_factor=args.iqr_factor, reference_date=args.reference_date)  # 실제 입력으로 필수 분석을 순서대로 실행한다.
    if analyzer.audit['rfm']['segment_count'] < 4 or analyzer.correlations()['pearson_r'].notna().sum() < 2:  # 과제의 그룹 수와 상관 분석 조건을 검사한다.
        raise ValueError('네 고객 그룹과 두 쌍 이상의 유효 상관관계를 만들 자료가 부족하다. 표본·기준을 확인해.')  # 결과를 억지로 쪼개 과제 완료처럼 표시하지 않는다.
    print('2/4 로컬 전처리 결과와 집계 저장', flush=True)  # 고객별 출력이 어디에 저장되는지 단계로 알린다.
    analyzer.save_processed(root / 'data/processed')  # 민감할 수 있는 결과는 Git 제외 폴더에 저장한다.
    print('3/4 필수 그래프 여섯 종류 생성', flush=True)  # 차트 생성 단계를 알린다.
    figures = build_charts(analyzer, root / 'reports/figures')  # 보고서용 PNG를 같은 데이터로 만든다.
    for figure in figures.values():  # 저장한 그림을 차례로 정리한다.
        plt.close(figure)  # 반복 실행 시 그림 메모리가 누적되지 않게 한다.
    print('4/4 수치 근거와 한계가 있는 분석 설명 저장', flush=True)  # 해석 문서 작성 단계를 알린다.
    (root / 'reports/analysis.md').write_text(analysis_markdown(analyzer))  # 실제 결과로 인사이트와 한계를 생성한다.
    print(f"완료: 고객 {analyzer.audit['customers']:,}명, 거래 {analyzer.audit['rows']:,}행, 실제 이미지 {analyzer.audit['images']['decoded_products']}개, 고객 그룹 {analyzer.audit['rfm']['segment_count']}개")  # 고객 번호 대신 검증한 집계만 출력한다.


if __name__ == '__main__':  # 이 파일을 직접 실행했을 때만 분석을 시작한다.
    main()  # 위에서 정의한 전체 실행 함수를 호출한다.
