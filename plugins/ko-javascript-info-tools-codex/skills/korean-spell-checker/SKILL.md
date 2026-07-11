---
name: korean-spell-checker
description: >
  Markdown 또는 일반 텍스트의 한국어 맞춤법과 띄어쓰기를 검사한다. 특히
  ko.javascript.info 한국어 번역 문서에 사용한다. 사용자가 맞춤법, 띄어쓰기,
  오탈자 검사, hanspell 실행, .md 한국어 문서 검토, Claude 맞춤법 검사
  워크플로의 Codex 변환을 요청할 때 사용한다.
---

# 한국어 맞춤법 검사

포함된 `scripts/check_spelling.py`로 `hanspell`을 실행하고 Markdown 또는 일반 텍스트의 한국어 맞춤법과 띄어쓰기 문제를 보고한다.

`$korean-spell-checker`는 Codex에서 스킬을 호출하는 문법이며 셸 명령어가 아니다. 터미널에서는 Python 스크립트를 직접 실행한다.

## 검사 절차

1. 검사 대상을 결정한다.
   - 사용자가 파일 경로를 주면 해당 파일을 검사한다.
   - 디렉터리 경로를 주면 `rg --files <디렉터리> | rg '\.md$'`로 Markdown 파일을 찾는다.
   - 대상이 불분명하면 파일 또는 디렉터리 경로를 요청한다.

2. 이 스킬 디렉터리에서 포함된 스크립트를 실행한다.

```bash
python3 scripts/check_spelling.py path/to/article.md
```

현재 작업 디렉터리가 스킬 디렉터리가 아니면 `scripts/check_spelling.py`의 절대 경로를 사용한다.

전역으로 설치한 스킬은 다음처럼 실행한다.

```bash
python3 ~/.codex/skills/korean-spell-checker/scripts/check_spelling.py path/to/article.md
```

3. JSON 출력을 해석한다.
   - `violations`에는 `line`, `problem`, `suggestion`, `explanation`, `severity`가 들어 있다.
   - 문제가 없으면 `passed`에 `맞춤법 오류 없음`이 들어 있다.
   - `filtered.masking_artifacts`는 Markdown 마스킹 때문에 비정상적으로 큰 공백이 생겨 제외한 결과 수다.
   - `filtered.non_korean`은 검사할 한글이 없는 순수 ASCII 또는 코드 문법 제안을 제외한 결과 수다.
   - 스크립트가 `error`를 반환하면 의존성 또는 실행 오류를 원문 그대로 보고한다.

4. 결과를 간결한 Markdown 표로 보고한다.

| 줄 | 규칙 ID | 문제 | 수정 제안 | 설명 |
|---:|---|---|---|---|

규칙 ID는 `SPELL`을 사용한다. 사용자가 완화된 편집 검토를 요청하지 않았다면 스크립트가 찾은 항목을 모두 필수로 분류한다.

## 실행 환경

Python 3, Node.js, `npx`가 필요하다. 스크립트는 `npx --yes hanspell -d`를 실행하므로 처음 실행할 때 `hanspell` npm 패키지를 내려받을 수 있다.

`npx`, Node.js 또는 `hanspell`을 사용할 수 없으면 중단하고 스크립트의 정확한 오류를 보고한다. 맞춤법 검사 결과를 임의로 만들지 않는다.

## 오탐 방지

- 인라인 코드에서는 백틱만 제거하고 내용을 보존한다. 따라서 `` `fetch`로 ``를 `fetch로` 형태로 검사한다.
- Markdown 링크와 이미지에서는 대상 주소를 제거하고 표시 문구를 보존한다. 따라서 `[명세서](url)에`를 `명세서에` 형태로 검사한다.
- `<info:fetch>`는 `fetch`로 보존하고 다른 HTML 태그는 공백을 추가하지 않고 제거한다.
- 코드 블록과 주석은 줄 번호를 유지한 채 마스킹한다.
- 네 칸 이상의 공백이 포함된 백엔드 결과는 원문이 아닌 마스킹 부산물로 보고 제외한다.
- 한글이 없는 결과는 코드 문장부호나 순수 ASCII 문법이므로 제외한다.
- 원문이 보호된 Markdown 영역 밖의 수정 가능한 텍스트와 명확히 대응할 때만 제안을 적용한다.

## 수정 지침

사용자가 수정을 명시적으로 요청하지 않았다면 파일을 변경하지 않는다.

수정할 때는 다음 원칙을 따른다.

- 코드 블록, 인라인 코드, URL, Markdown 이미지 대상, HTML 태그 밖의 텍스트만 변경한다.
- 원문이 여러 번 등장해 대상 위치가 모호하면 해당 수정을 건너뛴다.
- 한 번에 하나씩 수정하고 변경한 문맥을 다시 읽는다.
- 문장 전체를 다시 쓰거나 기술적 의미를 바꿀 수 있으면 자동 수정 대신 수동 제안으로 남긴다.
