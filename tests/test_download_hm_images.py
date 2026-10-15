import csv  # 가짜 이미지 목록을 만든다.
import io  # 테스트의 진행 출력을 메모리에서 받는다.
import json  # 다운로드 결과 기록을 읽는다.
import subprocess  # 시간 초과 상황을 만든다.
import unittest  # Python 기본 테스트 도구를 사용한다.
from contextlib import redirect_stdout  # 테스트 출력을 검사할 수 있게 모은다.
from pathlib import Path  # 임시 파일 경로를 다룬다.
from tempfile import TemporaryDirectory  # 실제 원본과 분리된 임시 폴더를 만든다.
from types import SimpleNamespace  # 가짜 Kaggle 실행 결과를 만든다.
from unittest.mock import patch  # 네트워크 요청을 가짜 동작으로 바꾼다.
from scripts import download_hm_images as module  # 검증할 다운로드 모듈을 가져온다.


class DownloadImagesTests(unittest.TestCase):  # 다운로드 경로와 실패 처리를 검증한다.
    def setUp(self):  # 각 테스트에 깨끗한 임시 프로젝트를 준비한다.
        self.folder = TemporaryDirectory(prefix='hm-download-test-')  # 테스트용 공간을 만든다.
        self.addCleanup(self.folder.cleanup)  # 테스트가 끝나면 가짜 파일을 정리한다.
        self.root = Path(self.folder.name)  # 가짜 프로젝트 경로를 지정한다.
        self.sample = self.root / 'data/sample'  # 가짜 표본 위치를 만든다.
        self.sample.mkdir(parents=True)  # 이미지 목록 폴더를 준비한다.
        self.raw = self.root / 'data/raw'  # 가짜 원본 위치를 정한다.
        self.raw.mkdir(parents=True)  # 기존 파일 재사용 검사도 가능하게 폴더를 만든다.
        self.values = [str(index).zfill(10) for index in range(200)]  # 가짜 상품 후보 200개를 만든다.
        with (self.sample / 'image_manifest.csv').open('w', newline='') as stream:  # 가짜 목록을 저장한다.
            writer = csv.writer(stream)  # CSV 쓰기 도구를 준비한다.
            writer.writerow(['article_id', 'file_path'])  # 목록 헤더를 쓴다.
            writer.writerows((value, f'images/{value[:3]}/{value}.jpg') for value in self.values)  # 허용된 경로만 목록에 넣는다.
        self.jpeg = b'\xff\xd8test\xff\xd9'  # 기본 표시 검사만을 위한 가짜 JPEG다.

    def read_report(self):  # 저장된 결과를 다시 읽는다.
        return json.loads((self.sample / 'image_download_summary.json').read_text())  # 기록 내용을 반환한다.

    def check_layout(self, nested):  # 실제 Kaggle처럼 저장하는 경우와 하위 경로를 보존하는 경우를 검사한다.
        calls = []  # 요청 횟수를 확인한다.
        def fake_download(args, **kwargs):  # 외부 요청 없이 파일을 저장한다.
            self.assertIn('-f', args)  # 전체 다운로드를 요청하면 안 된다.
            calls.append(args)  # 개별 요청을 기록한다.
            if len(calls) == 1:  # 첫 후보가 없을 때 보충하는 동작도 검사한다.
                return SimpleNamespace(returncode=1, stderr='404 Not Found')  # 안전한 가짜 서버 실패를 반환한다.
            expected = Path(args[args.index('-f') + 1])  # 서버에서 요청한 경로를 읽는다.
            destination = Path(args[args.index('-p') + 1])  # 실제 저장 폴더를 읽는다.
            target = destination / (expected if nested else expected.name)  # Kaggle 버전별 저장 방식 차이를 재현한다.
            target.parent.mkdir(parents=True, exist_ok=True)  # 가짜 이미지 폴더를 만든다.
            target.write_bytes(self.jpeg)  # 기본 표시가 있는 가짜 파일을 저장한다.
            return SimpleNamespace(returncode=0)  # 다운로드 성공을 반환한다.
        with patch.object(module.shutil, 'which', return_value='fake-kaggle'), patch.object(module.subprocess, 'run', side_effect=fake_download), redirect_stdout(io.StringIO()):  # 실제 Kaggle을 호출하지 않는다.
            module.download(self.root)  # 기본 목표 100개를 준비한다.
        report = self.read_report()  # 생성 결과를 다시 읽는다.
        self.assertEqual(len(calls), 101)  # 실패 1개와 성공 100개 뒤 요청이 멈춰야 한다.
        self.assertEqual(report['ready'], 100)  # 저장된 성공 수가 맞아야 한다.
        self.assertEqual(report['failure_details'][0]['reason'], 'not_found')  # 없는 파일을 권한 오류와 구분해야 한다.
        self.assertTrue(all(module.has_jpeg_markers(self.raw / name) for name in report['files']))  # 모든 파일이 최종 폴더에 있어야 한다.
        self.assertFalse(list(self.raw.glob('.hm-download-*')))  # 임시 다운로드가 정리돼야 한다.
        with patch.object(module.shutil, 'which', return_value='fake-kaggle'), patch.object(module.subprocess, 'run', return_value=SimpleNamespace(returncode=1, stderr='404 Not Found')) as runner, redirect_stdout(io.StringIO()):  # 재실행 시 없는 첫 후보만 실패하도록 한다.
            module.download(self.root, limit=1)  # 이미 받은 첫 성공 파일까지 확인한다.
        self.assertEqual(runner.call_count, 1)  # 앞서 실패했던 첫 후보만 재요청하고 기존 성공 파일은 재사용한다.

    def test_flattened_filenames(self):  # 설치된 Kaggle 2.2.4의 실제 저장 방식을 재현한다.
        self.check_layout(nested=False)  # 파일명만 저장돼도 최종 경로에 배치돼야 한다.

    def test_preserved_subdirectories(self):  # 하위 경로를 보존하는 버전도 지원한다.
        self.check_layout(nested=True)  # 원래 전체 상대 경로로 저장해도 성공해야 한다.

    def test_reuse_legacy_file_without_request(self):  # 이전 코드가 이미 받은 파일을 보존하면서 재사용한다.
        legacy = self.raw / (self.values[0] + '.jpg')  # 잘못된 위치의 기존 파일 경로를 만든다.
        legacy.write_bytes(self.jpeg)  # 기존 다운로드 파일을 재현한다.
        with patch.object(module.shutil, 'which', return_value='fake-kaggle'), patch.object(module.subprocess, 'run') as runner, redirect_stdout(io.StringIO()):  # 네트워크가 없어야 하는 상황이다.
            module.download(self.root, limit=1)  # 기존 파일 한 개를 올바른 위치에 준비한다.
        runner.assert_not_called()  # 같은 이미지를 다시 요청하지 않아야 한다.
        self.assertEqual(legacy.read_bytes(), self.jpeg)  # 기존 파일이 보존돼야 한다.
        self.assertEqual((self.raw / self.read_report()['files'][0]).read_bytes(), self.jpeg)  # 최종 위치에도 같은 내용이 있어야 한다.

    def test_permission_failure_hides_raw_output(self):  # 오류 설명이 인증 정보를 노출하지 않는지 검사한다.
        secret = 'PRIVATE_TEST_SENTINEL'  # 실제 비밀이 아닌 검사용 문자열이다.
        output = io.StringIO()  # 화면 출력을 확인할 공간이다.
        result = SimpleNamespace(returncode=1, stderr=f'403 Forbidden {secret}', stdout='')  # 가짜 권한 오류다.
        with patch.object(module.shutil, 'which', return_value='fake-kaggle'), patch.object(module.subprocess, 'run', return_value=result) as runner, redirect_stdout(output):  # 실제 요청 대신 가짜 오류를 낸다.
            with self.assertRaises(SystemExit):  # 목표 미달이면 완료로 끝나면 안 된다.
                module.download(self.root)  # 5회 연속 실패를 검사한다.
        report = self.read_report()  # 저장된 안전한 기록을 읽는다.
        self.assertEqual(runner.call_count, 5)  # 연속 실패 5번에서 멈춰야 한다.
        self.assertEqual({item['reason'] for item in report['failure_details']}, {'permission'})  # 권한 분류만 남겨야 한다.
        self.assertNotIn(secret, output.getvalue() + json.dumps(report))  # 원본 오류 문자열은 화면과 기록에 없어야 한다.

    def test_success_without_file_is_path_failure(self):  # 성공 코드만 반환된 경우 파일 존재까지 검사한다.
        result = SimpleNamespace(returncode=0)  # 파일은 만들지 않은 가짜 명령 성공이다.
        with patch.object(module.shutil, 'which', return_value='fake-kaggle'), patch.object(module.subprocess, 'run', return_value=result), redirect_stdout(io.StringIO()):  # 실제 요청을 막는다.
            with self.assertRaises(SystemExit):  # 성공 파일이 없으므로 중단해야 한다.
                module.download(self.root)  # 저장 위치 문제를 검사한다.
        self.assertEqual({item['reason'] for item in self.read_report()['failure_details']}, {'missing_file'})  # 경로 문제를 인증 문제와 구분해야 한다.

    def test_timeout_is_reported(self):  # 네트워크가 오래 걸릴 때 안전하게 중단한다.
        with patch.object(module.shutil, 'which', return_value='fake-kaggle'), patch.object(module.subprocess, 'run', side_effect=subprocess.TimeoutExpired('fake', 120)), redirect_stdout(io.StringIO()):  # 시간 초과만 재현한다.
            with self.assertRaises(SystemExit):  # 목표 미달이므로 종료해야 한다.
                module.download(self.root)  # 시간 초과 분류를 확인한다.
        self.assertEqual({item['reason'] for item in self.read_report()['failure_details']}, {'timeout'})  # 시간 초과가 기록돼야 한다.
        self.assertFalse(list(self.raw.glob('.hm-download-*')))  # 실패한 임시 폴더도 정리돼야 한다.

    def test_invalid_download_is_not_published(self):  # 잘못 받은 파일을 최종 이미지로 보관하지 않는다.
        def invalid_download(args, **kwargs):  # 성공 코드와 잘못된 파일을 함께 반환한다.
            value = Path(args[args.index('-f') + 1]).name  # 요청한 이미지 파일명을 꺼낸다.
            (Path(args[args.index('-p') + 1]) / value).write_bytes(b'invalid-image')  # 가짜 손상 파일을 만든다.
            return SimpleNamespace(returncode=0)  # 명령만 성공한 것으로 처리한다.
        with patch.object(module.shutil, 'which', return_value='fake-kaggle'), patch.object(module.subprocess, 'run', side_effect=invalid_download), redirect_stdout(io.StringIO()):  # 실제 요청 없이 오류를 재현한다.
            with self.assertRaises(SystemExit):  # 잘못된 이미지는 완료로 세면 안 된다.
                module.download(self.root)  # 기본 형식 검사 실패를 확인한다.
        self.assertEqual({item['reason'] for item in self.read_report()['failure_details']}, {'invalid_jpeg'})  # 형식 오류 분류를 기록해야 한다.
        self.assertFalse(list(self.raw.rglob('*.jpg')))  # 실패한 파일이 최종 위치나 임시 위치에 남으면 안 된다.

    def test_existing_invalid_target_is_preserved(self):  # 기존 손상 파일을 자동 덮어쓰지 않는다.
        target = self.raw / f'images/{self.values[0][:3]}/{self.values[0]}.jpg'  # 기존 최종 위치를 지정한다.
        target.parent.mkdir(parents=True)  # 가짜 기존 폴더를 만든다.
        target.write_bytes(b'existing-content')  # 기본 검사에 실패할 기존 파일을 만든다.
        with patch.object(module.shutil, 'which', return_value='fake-kaggle'), patch.object(module.subprocess, 'run') as runner:  # 외부 요청이 없어야 한다.
            with self.assertRaises(ValueError):  # 기존 파일을 검사 후 중단해야 한다.
                module.download(self.root)  # 기존 파일 보호를 검사한다.
        runner.assert_not_called()  # 덮어쓸 다운로드를 요청하지 않는다.
        self.assertEqual(target.read_bytes(), b'existing-content')  # 기존 내용이 그대로여야 한다.


if __name__ == '__main__':  # 이 파일을 직접 실행할 때도 검사를 시작한다.
    unittest.main()  # 전체 테스트를 실행한다.
