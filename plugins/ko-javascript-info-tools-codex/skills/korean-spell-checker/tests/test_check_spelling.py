from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "check_spelling.py"
SPEC = importlib.util.spec_from_file_location("check_spelling", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class PrepareContentTests(unittest.TestCase):
    def test_keeps_inline_code_attached_to_particle(self) -> None:
        self.assertEqual(CHECKER.prepare_content("`fetch`로 요청합니다."), "fetch로 요청합니다.")

    def test_keeps_link_label_attached_to_particle(self) -> None:
        self.assertEqual(
            CHECKER.prepare_content("[명세서](https://example.com)에 따릅니다."),
            "명세서에 따릅니다.",
        )

    def test_keeps_info_reference_attached_to_particle(self) -> None:
        self.assertEqual(CHECKER.prepare_content("<info:fetch>로 이동합니다."), "fetch로 이동합니다.")

    def test_removes_emphasis_without_splitting_particles(self) -> None:
        self.assertEqual(CHECKER.prepare_content("**강조**는 유지합니다."), "강조는 유지합니다.")

    def test_keeps_image_label_attached_to_particle(self) -> None:
        self.assertEqual(
            CHECKER.prepare_content("![구조도](diagram.png)는 예시입니다."),
            "구조도는 예시입니다.",
        )

    def test_masks_fenced_code_and_preserves_line_count(self) -> None:
        source = "앞 문장\n```js\nconst value = '검사 제외';\n```\n뒤 문장"
        cleaned = CHECKER.prepare_content(source)
        self.assertEqual(cleaned.count("\n"), source.count("\n"))
        self.assertNotIn("검사 제외", cleaned)


class ArtifactFilterTests(unittest.TestCase):
    def test_filters_large_masking_gap(self) -> None:
        self.assertTrue(CHECKER.is_masking_artifact("fetch        로", "fetch로"))

    def test_keeps_normal_double_space_finding(self) -> None:
        self.assertFalse(CHECKER.is_masking_artifact("단어  사이", "단어 사이"))

    def test_filters_pure_ascii_code_suggestion(self) -> None:
        self.assertTrue(CHECKER.is_non_korean_finding("xhr.open('POST', ...)"))

    def test_keeps_mixed_identifier_and_korean_particle(self) -> None:
        self.assertFalse(CHECKER.is_non_korean_finding("fetch로"))


if __name__ == "__main__":
    unittest.main()
