import unittest  # 보고서가 변수 이름과 해석을 잃지 않는지 검사한다.
from types import SimpleNamespace  # 분석 전체를 실행하지 않는 작은 검사 대상을 만든다.
import pandas as pd  # 정답을 손으로 계산할 작은 표를 만든다.
from src.reporting import markdown_table, statistics_interpretations  # 실제 보고서 변환과 해석 함수를 가져온다.


class ReportingTests(unittest.TestCase):  # 보고서를 읽을 수 없게 되는 회귀를 막는다.
    def test_unnamed_feature_labels_are_preserved(self):  # 이름 없는 인덱스의 변수명이 빠지던 오류를 검사한다.
        frame = pd.DataFrame({'mean': [2.0, 6.0]}, index=['price', 'product_name_length'])  # 의미 있는 행 이름을 넣는다.
        result = markdown_table(frame)  # 실제 Markdown 변환을 실행한다.
        self.assertIn('| price | 2.0000 |', result)  # 가격 변수명이 숫자 옆에 남아 있어야 한다.
        self.assertIn('| product_name_length | 6.0000 |', result)  # 다른 변수명도 구분할 수 있어야 한다.

    def test_default_row_numbers_do_not_add_a_column(self):  # 기본 행 번호를 새 분석 변수처럼 출력하지 않는다.
        result = markdown_table(pd.DataFrame({'left': ['price'], 'right': ['image_mean']}))  # 상관관계 표와 같은 기본 인덱스를 만든다.
        self.assertEqual(result.splitlines()[0], '| left | right |')  # 실제 열 두 개만 표 머리글에 있어야 한다.

    def test_named_segment_labels_are_preserved(self):  # 기존 그룹별 표도 그대로 읽을 수 있어야 한다.
        frame = pd.DataFrame({'customers': [3]}, index=pd.Index(['Recent high value'], name='segment'))  # 이름 있는 그룹 인덱스를 만든다.
        result = markdown_table(frame)  # 같은 변환기로 그룹 표를 만든다.
        self.assertIn('| segment | customers |', result)  # 그룹 이름표의 제목을 유지한다.
        self.assertIn('| Recent high value | 3 |', result)  # 고객 수와 그룹 이름의 연결을 유지한다.

    def test_interpretations_use_actual_values_and_scope(self):  # 숫자·단위·해석의 연결을 정답 표로 검사한다.
        frame = pd.DataFrame({'price': [1.0, 3.0], 'product_name_length': [4.0, 8.0], 'description_length': [10.0, 30.0], 'image_mean': [0.25, 0.75], 'image_std': [0.1, 0.3]})  # 평균과 사분위수를 손으로 확인할 자료다.
        analyzer = SimpleNamespace(summary_statistics=lambda: frame.describe().T)  # 실제 분석기와 같은 통계 반환 형태를 제공한다.
        paragraphs = statistics_interpretations(analyzer)  # 보고서와 노트북의 공통 해석을 만든다.
        self.assertEqual(len(paragraphs), 5)  # 다섯 변수 모두 설명해야 한다.
        self.assertIn('평균 2.000000, 중앙값 2.000000, 표준편차 1.414214, Q1 1.500000, Q3 2.500000', paragraphs[0])  # 계산된 수치가 정확한지 확인한다.
        self.assertIn('채운 설명 길이도 포함', paragraphs[2])  # 대치한 값이 섞인 분포임을 밝혀야 한다.
        self.assertIn('사진이 있는 구매 행 기준', paragraphs[3])  # 사진 수와 구매 행 수를 구분해야 한다.
        self.assertIn('다시 얼마나 다른지', paragraphs[4])  # 이미지 피처 자체의 퍼짐과 통계표의 표준편차를 구분한다.

    def test_missing_images_are_not_reported_as_zero(self):  # 사진이 없을 때 관측값 0처럼 설명하지 않는다.
        frame = pd.DataFrame({'price': [1.0, 3.0], 'product_name_length': [4.0, 8.0], 'description_length': [10.0, 30.0], 'image_mean': [float('nan'), float('nan')], 'image_std': [float('nan'), float('nan')]})  # 이미지 특성만 관측하지 못한 표다.
        analyzer = SimpleNamespace(summary_statistics=lambda: frame.describe().T)  # 관측 개수 0을 반환할 통계를 만든다.
        paragraphs = statistics_interpretations(analyzer)  # 빈 이미지 특성의 해석을 확인한다.
        self.assertTrue(all('해석을 보류' in paragraph for paragraph in paragraphs[3:]))  # 관측하지 않은 값에는 결론을 내리지 않는다.
        self.assertNotIn('평균 0.000000', '\n'.join(paragraphs[3:]))  # 없는 자료를 실제 평균 0이라고 표시하지 않는다.


if __name__ == '__main__':  # 이 파일만 직접 실행할 때도 검사할 수 있게 한다.
    unittest.main()  # 준비한 회귀 검사를 실행한다.
