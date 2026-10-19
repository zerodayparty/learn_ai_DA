import csv  # 작은 정답 데이터로 표를 만든다.
import tempfile  # 실제 H&M 파일과 별도인 테스트 공간을 만든다.
import unittest  # Python 기본 테스트 도구를 사용한다.
from pathlib import Path  # 테스트용 데이터 경로를 만든다.
import numpy as np  # 정답 픽셀과 배열 비교에 사용한다.
import pandas as pd  # 숫자 표의 기대 결과를 확인한다.
from src.pipeline import DataAnalyzer, SEGMENTS  # 실제로 사용하는 분석 도구를 검사한다.
from matplotlib.image import imsave  # 과제에서 허용한 Matplotlib로 테스트 이미지를 저장한다.


class PipelineTests(unittest.TestCase):  # 분석 결과의 의미가 바뀌는 실수를 검사한다.
    def setUp(self):  # 모든 검사에 독립적인 입력을 만든다.
        self.folder = tempfile.TemporaryDirectory(prefix='hm-pipeline-test-')  # 실제 데이터가 없는 임시 폴더다.
        self.addCleanup(self.folder.cleanup)  # 검사가 끝나면 가짜 파일을 정리한다.
        self.root = Path(self.folder.name)  # 테스트 프로젝트 위치를 정한다.
        self.sample = self.root / 'sample'  # 가짜 거래와 상품 위치를 정한다.
        self.sample.mkdir()  # CSV를 담을 폴더를 만든다.
        header = ['t_dat', 'customer_id', 'article_id', 'price', 'sales_channel_id']  # 실제 H&M 거래와 같은 구조다.
        self.rows = [['2020-09-21', 'fake_A', '1', 0.4, 1]] * 4 + [['2020-09-20', 'fake_B', '2', 0.01, 1]] + [['2019-11-27', 'fake_C', '3', 0.6, 2]] * 3 + [['2019-08-19', 'fake_D', '4', 0.01, 2]]  # 네 그룹을 예상할 수 있는 구매 이력이다.
        with (self.sample / 'transactions.csv').open('w', newline='') as stream:  # 테스트 거래를 저장한다.
            writer = csv.writer(stream)  # CSV 저장 도구를 준비한다.
            writer.writerow(header)  # 필수 컬럼을 쓴다.
            writer.writerows(self.rows)  # 반복 구매도 그대로 기록한다.
        with (self.sample / 'articles.csv').open('w', newline='') as stream:  # 테스트 상품을 저장한다.
            writer = csv.writer(stream)  # 상품 CSV 도구를 준비한다.
            writer.writerow(['article_id', 'product_group_name', 'prod_name', 'detail_desc'])  # 상품 연결·글 특성에 필요한 컬럼이다.
            writer.writerows([['1', 'Tops', 'aa', 'long'], ['2', 'Tops', 'bbb', ''], ['3', 'Outer', 'cccc', 'xx'], ['4', 'Unknown', 'ddddd', '']])  # 두 상품의 실제 결측치를 만든다.
        self.analyzer = DataAnalyzer(self.sample, self.root / 'images', min_rows=1)  # 테스트만 최소 규모 조건을 완화한다.

    def test_join_preserves_repeat_rows_and_zero_prefix(self):  # 반복 행 보존과 상품 연결을 검사한다.
        frame = self.analyzer.load_data()  # 실제 연결 코드를 실행한다.
        self.assertEqual(len(frame), 9)  # 구매 반복을 삭제하면 안 된다.
        self.assertEqual(frame['article_id'].nunique(), 4)  # 상품 수와 구매 행 수는 다르다.
        self.assertTrue(frame['article_id'].str.len().eq(10).all())  # 이미지와 연결할 앞의 0을 보존한다.
        self.assertEqual(self.analyzer.audit['repeated_rows_preserved'], 5)  # 같은 날짜·상품을 여러 번 산 기록을 보존한다.

    def test_duplicate_article_rejected(self):  # 잘못된 상품 표로 거래가 늘어나는 것을 막는다.
        articles = pd.read_csv(self.sample / 'articles.csv')  # 가짜 상품 표를 읽는다.
        pd.concat([articles, articles.iloc[:1]]).to_csv(self.sample / 'articles.csv', index=False)  # 상품 한 개를 중복시킨다.
        with self.assertRaises(ValueError):  # 중복 상품은 조용히 통과하면 안 된다.
            self.analyzer.load_data()  # 연결 전 중복 검사를 실행한다.

    def test_missing_article_rejected(self):  # 상품 정보 없는 거래를 버리고 진행하지 않는다.
        articles = pd.read_csv(self.sample / 'articles.csv')  # 가짜 상품 표를 읽는다.
        articles.iloc[1:].to_csv(self.sample / 'articles.csv', index=False)  # 구매된 상품 하나의 정보를 없앤다.
        with self.assertRaises(ValueError):  # 상품 연결 누락을 찾아야 한다.
            self.analyzer.load_data()  # 누락 검사 코드를 실행한다.

    def test_invalid_identifier_rejected(self):  # 상품 번호를 임의 파일 경로로 쓸 수 없게 한다.
        with self.assertRaises(ValueError):  # 파일 경로 문자열은 상품 번호가 아니다.
            DataAnalyzer.normalize_ids(pd.Series(['../outside']))  # 외부 경로를 상품 번호로 넣어 본다.

    def test_missing_features_use_product_not_transaction_weights(self):  # 많이 산 상품이 대치 통계를 지배하지 않는지 검사한다.
        self.analyzer.df = pd.DataFrame({'article_id': ['a'] * 5 + ['b', 'c'], 'product_group_name': ['Tops'] * 7, 'description_length': [4.0] * 5 + [20.0, np.nan]})  # 상품 a만 다섯 번 구매한 표다.
        self.analyzer.handle_missing_values()  # 상품당 한 번씩 계산한 그룹 중앙값을 적용한다.
        result = self.analyzer.df.loc[self.analyzer.df['article_id'].eq('c'), 'description_length'].iloc[0]  # 결측 상품 결과를 읽는다.
        self.assertEqual(result, 12.0)  # 정답은 상품 값 4와 20의 중앙값이며 거래 가중 중앙값 4가 아니다.

    def test_all_missing_group_uses_global_fallback(self):  # 그룹 전체가 비면 전체 상품 통계로 보완한다.
        self.analyzer.load_data()  # 상품 표를 연결한다.
        self.analyzer.add_text_features()  # 없는 설명 길이를 결측치로 만든다.
        self.analyzer.handle_missing_values()  # 그룹 중앙값 대치를 실행한다.
        unknown = self.analyzer.df.loc[self.analyzer.df['product_group_name'].eq('Unknown')].iloc[0]  # 가짜 결측 그룹을 확인한다.
        self.assertEqual(unknown['description_length'], 3.0)  # 전체 관측 상품 길이 4와 2의 중앙값이어야 한다.
        self.assertTrue(unknown['description_length_was_missing'])  # 채운 값을 실제 관측값과 구분해야 한다.

    def test_iqr_does_not_change_original_amount(self):  # 분포 비교가 실제 구매 금액을 바꾸지 않아야 한다.
        self.analyzer.df = pd.DataFrame({'price': [1.0, 2.0, 2.0, 3.0, 100.0], 'amount': [1.0, 2.0, 2.0, 3.0, 100.0]})  # IQR 정답이 명확한 표다.
        original = self.analyzer.df['amount'].copy()  # 원래 금액을 보관한다.
        mask = self.analyzer.detect_outliers()  # 이상치와 비교용 사본을 계산한다.
        self.assertEqual(mask.tolist(), [False, False, False, False, True])  # 100만 이상치여야 한다.
        self.assertEqual(self.analyzer.df['price_clipped'].iloc[-1], 4.5)  # Q3 3에 IQR 1의 1.5배를 더한 상한이다.
        pd.testing.assert_series_equal(original, self.analyzer.df['amount'])  # RFM에 쓰는 원래 금액은 바뀌면 안 된다.

    def test_pixel_mean_std_and_grayscale(self):  # 픽셀 배열 연산의 정답을 독립적으로 확인한다.
        gray = np.array([[0, 255], [255, 0]], dtype=np.uint8)  # 검정과 흰색이 반씩 있는 이미지다.
        features = DataAnalyzer.image_statistics(gray)  # 흑백도 같은 기준으로 처리한다.
        self.assertEqual(features['image_mean'], 0.5)  # 정규화 후 평균은 0.5다.
        self.assertEqual(features['image_std'], 0.5)  # 모집단 표준편차도 0.5다.
        with self.assertRaises(ValueError):  # 잘못된 픽셀 범위를 조용히 허용하지 않는다.
            DataAnalyzer.image_statistics(np.full((2, 2, 3), 2.0))  # 정규화하지 않은 실수 픽셀을 넣어 본다.

    def test_rfm_values_four_groups_and_reference_date(self):  # 고객 분석의 숫자와 그룹 의미를 검사한다.
        self.analyzer.load_data()  # 가짜 고객 네 명의 전체 이력을 읽는다.
        result = self.analyzer.calculate_rfm(reference_date='2020-09-22').set_index('customer_id')  # 정해진 기준일로 계산한다.
        self.assertEqual(result.loc['fake_A', 'frequency'], 4)  # 같은 날 네 번 구매도 네 행으로 계산한다.
        self.assertEqual(result.loc['fake_A', 'recency'], 1)  # 기준일보다 하루 전 구매한 고객이다.
        self.assertAlmostEqual(result.loc['fake_A', 'monetary'], 1.6)  # 0.4를 네 번 산 금액이다.
        self.assertEqual(set(result['segment']), set(SEGMENTS))  # 예상한 네 그룹이 모두 나타나야 한다.
        self.assertEqual(result.loc['fake_C', 'segment'], 'No recent purchase / Frequent & high spending')  # 과거 고빈도·고금액 고객을 구분한다.
        daily = self.analyzer.calculate_rfm(reference_date='2020-09-22', frequency='purchase_days').set_index('customer_id')  # 구매일 수라는 다른 정의도 명시적으로 선택할 수 있다.
        self.assertEqual(daily.loc['fake_A', 'frequency'], 1)  # 주문 수와 구매 행 수를 혼동하지 않는다.

    def test_reference_before_last_purchase_rejected(self):  # 미래 거래가 있는 과거 기준일을 막는다.
        self.analyzer.load_data()  # 가짜 이력을 읽는다.
        with self.assertRaises(ValueError):  # 기준일 오류가 발생해야 한다.
            self.analyzer.calculate_rfm(reference_date='2019-01-01')  # 마지막 거래보다 이른 기준일을 넣는다.

    def test_image_subset_preserves_rows_and_private_outputs_are_local(self):  # 이미지 연결로 표본을 줄이지 않고 로컬에만 고객 표를 저장한다.
        image_dir = self.root / 'images/000'  # 가짜 상품 번호 앞 세 자리 폴더다.
        image_dir.mkdir(parents=True)  # 가짜 이미지 위치를 만든다.
        imsave(image_dir / '0000000001.jpg', np.full((4, 4, 3), 127, dtype=np.uint8))  # 실제 디코딩할 수 있는 작은 JPEG를 만든다.
        self.analyzer.run(min_images=1, reference_date='2020-09-22')  # 전체 분석을 작은 정답 자료에서 실행한다.
        self.assertEqual(len(self.analyzer.df), 9)  # 사진이 없는 거래도 남아야 한다.
        self.assertEqual(self.analyzer.audit['images']['covered_transaction_rows'], 4)  # 한 사진이 네 구매 행에 연결돼야 한다.
        self.assertEqual(self.analyzer.df['has_image'].sum(), 4)  # 결측 사진을 0 밝기 사진으로 만들지 않는다.
        self.assertTrue(self.analyzer.correlations()['pearson_r'].isna().iloc[1])  # 사진 한 개만으로 상관관계를 만들지 않는다.
        self.assertNotIn('customer_id', self.analyzer.safe_preview().columns)  # 공개 미리보기에는 고객 번호가 없어야 한다.
        self.analyzer.save_processed(self.root / 'processed')  # 테스트의 임시 로컬 결과로 저장한다.
        self.assertTrue((self.root / 'processed/customer_rfm.csv').is_file())  # 고객 표는 지정한 로컬 결과에만 있어야 한다.


if __name__ == '__main__':  # 직접 실행할 때도 같은 검사를 수행한다.
    unittest.main()  # 회귀 검사를 실행한다.
