---
name: korean-spell-checker
description: Markdown 또는 일반 텍스트 번역의 한국어 맞춤법과 띄어쓰기를 검사한다. 특히 ko.javascript.info 한국어 문서에 사용한다. 사용자가 맞춤법, 띄어쓰기, 오탈자 검사, hanspell 실행, .md 파일의 한국어 맞춤법 검토 또는 Claude 맞춤법 검사 워크플로의 Codex 변환을 요청할 때 사용한다.
---

# 한국어 맞춤법 검사

저장소의 `scripts/check_spelling.py` 스크립트로 `hanspell`을 실행하고 Markdown 또는 일반 텍스트 파일의 한국어 맞춤법과 띄어쓰기 문제를 보고한다.

## 검사 절차

1. 검사할 파일을 결정한다.
   - 사용자가 파일 경로를 제공하면 해당 파일을 검사한다.
   - 사용자가 디렉터리를 제공하면 `rg --files <dir> | rg '\.md$'`로 그 아래의 Markdown 파일을 찾는다.
   - 검사 대상이 명확하지 않으면 파일 또는 디렉터리 경로를 요청한다.

2. 이 스킬 디렉터리에서 저장소 루트의 스크립트를 실행한다.

```bash
python3 ../../scripts/check_spelling.py path/to/article.md
```

현재 작업 디렉터리가 스킬 디렉터리가 아니면 저장소 루트의 `scripts/check_spelling.py` 절대 경로를 사용한다.

3. JSON 출력을 해석한다.
   - `violations`에는 `line`, `problem`, `suggestion`, `explanation`, `severity`가 들어 있다.
   - 문제가 없으면 `passed`에 `맞춤법 오류 없음`이 들어 있다.
   - 스크립트가 `error`를 반환하면 의존성 또는 실행 문제를 그대로 보고한다.

4. 결과를 간결한 Markdown 표로 보고한다.

| 줄 | 규칙 ID | 문제 | 수정 제안 | 설명 |
|---:|---|---|---|---|

규칙 ID로 `SPELL`을 사용하고, 사용자가 완화된 편집 검토를 요청하지 않았다면 스크립트가 찾은 모든 항목을 `required`로 분류한다.

## 실행 환경

스크립트를 실행하려면 Python 3, Node.js, `npx`가 필요하다. 스크립트는 `npx --yes hanspell -d`를 실행하므로 처음 실행할 때 `hanspell` npm 패키지를 내려받을 수 있다.

`npx`, Node.js 또는 `hanspell`을 사용할 수 없으면 중단하고 스크립트의 정확한 오류를 보고한다. 맞춤법 검사 결과를 임의로 만들지 않는다.

## 수정 지침

사용자가 수정을 명시적으로 요청하지 않았다면 파일을 변경하지 않는다.

수정할 때는 다음 원칙을 따른다.

- 코드 블록, 인라인 코드, URL, Markdown 이미지 대상, HTML 태그 밖의 텍스트만 변경한다.
- 원문이 여러 번 등장해 대상 위치가 모호하면 해당 수정을 건너뛴다.
- 한 번에 하나씩 수정하고 계속하기 전에 변경한 부분을 다시 읽는다.
- 문장 전체를 다시 쓰거나 기술적 의미를 바꿀 수 있는 수정은 수동 제안으로 남긴다.
