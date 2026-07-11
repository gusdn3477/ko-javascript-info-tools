---
name: javascriptinfo-ko-translation-validator
description: >
  ko.javascript.info 한국어 Markdown 번역을 WIKI 번역 모범 사례, KIGO IT 스타일,
  프로젝트 커스텀 규칙, 한국어 맞춤법 기준으로 검증하고 선택적으로 수정한다.
  "번역 검토해줘", "번역 확인해줘", "번역 검증해줘", "번역 피드백",
  "번역 규칙 맞는지 봐줘", "번역 검사해줘" 요청이나 번역된 .md 파일이
  포함된 PR 검토, 검증 JSON 저장, 검증 결과에 따른 안전한 수정 요청에 사용한다.
---

# ko.javascript.info 번역 검증

Claude `translation-validator`와 같은 네 가지 검사를 실행하고, 결과를 병합해 한국어 보고서와 JSON으로 저장한 뒤 선택에 따라 안전한 항목을 수정한다.

## 검증 절차

### 1단계 — 대상 파일 결정

1. 대상 경로를 절대 경로로 변환한다.
2. 파일 경로이면 해당 파일을 검증한다.
3. 디렉터리 경로이면 `rg --files <디렉터리> | rg '\.md$'`로 Markdown 파일을 정렬해 찾고 파일별로 전체 절차를 순차 실행한다.
4. 대상이 없으면 `검토할 번역 문서의 파일 또는 디렉터리 경로를 알려 주세요.`라고 질문한다.
5. 대상 파일 전체와 다음 참조 문서를 읽는다.
   - [wiki-guidelines.md](references/wiki-guidelines.md)
   - [kigo-guidelines.md](references/kigo-guidelines.md)
   - [custom-rules.md](references/custom-rules.md)

참조 문서와 스크립트 경로는 이 `SKILL.md` 위치를 기준으로 계산한다. 현재 작업 디렉터리가 스킬 디렉터리라고 가정하지 않는다.

### 2단계 — 네 검사 병렬 실행

WIKI, KIGO, CUSTOM, SPELL 검사는 서로 독립적으로 실행한다. 협업 도구가 있으면 WIKI·KIGO·CUSTOM 하위 에이전트 세 개를 동시에 시작하고 메인 에이전트에서 SPELL을 실행한다. 협업 도구가 없으면 메인 에이전트에서 세 규칙을 구분해 차례대로 검사한다.

각 규칙 하위 에이전트에는 다음 정보만 전달한다.

- 검증 대상 절대 경로
- 담당 참조 문서 절대 경로 하나
- 담당 규칙 접두사와 `source`
- 아래 JSON 형식
- 공통 제외 범위와 줄 번호 규칙

각 하위 에이전트는 대상과 참조 문서를 읽고 JSON만 반환한다.

```json
{
  "source": "wiki | kigo | custom",
  "violations": [
    {
      "line": 1,
      "rule_id": "WIKI-N | KIGO-N | CUSTOM-N",
      "problem": "원문의 정확한 위반 문자열 또는 위반 내용",
      "suggestion": "정확한 대체 문자열 또는 수동 수정 제안",
      "severity": "required | recommended | info"
    }
  ],
  "passed": ["통과한 규칙 항목"]
}
```

담당 범위는 다음과 같다.

- **WIKI**: `wiki-guidelines.md`의 모든 `WIKI-*` 규칙, `source: "wiki"`
- **KIGO**: `kigo-guidelines.md`의 모든 `KIGO-*` 규칙, `source: "kigo"`
- **CUSTOM**: `custom-rules.md`의 모든 `CUSTOM-*` 규칙, `source: "custom"`

SPELL은 같은 플러그인에 포함된 Codex 맞춤법 스킬의 기본 `hanspell` 백엔드로 실행한다.

```bash
python3 <이-스킬-디렉터리>/../korean-spell-checker/scripts/check_spelling.py <대상-절대경로>
```

맞춤법 결과의 `line`, `problem`, `suggestion`, `explanation`을 보존하고 각 항목을 `rule_id: "SPELL"`, `source: "spell"`, `severity: "required"`로 정규화한다. 스크립트가 없거나 실패하면 오류 원문을 보존해 SPELL을 생략 처리한다. 결과를 임의로 만들거나 생략한 검사를 통과로 표시하지 않는다.

### 3단계 — 결과 검증 및 병합

모든 검사에 다음 기준을 적용한다.

- 위반 사항은 정확한 1부터 시작하는 원문 줄 번호를 기록한다. 맞춤법 백엔드가 위치를 찾지 못한 경우에만 `null`을 사용한다.
- 코드 블록, 인라인 코드, URL, Markdown 이미지 대상, HTML 태그, 원문 인용은 언어 규칙 검사에서 제외한다.
- Markdown 헤딩은 `WIKI-15` 검사 대상에 포함한다.
- `CUSTOM-병기`는 파일 전체에서 용어의 첫 등장만 검사한다.
- 명백한 위반과 맞춤법 오류는 `required`, 맥락에 따른 스타일 개선은 `recommended`, 사람의 판단이 필요한 의견은 `info`로 분류한다.
- 안전한 직접 치환은 `problem`에 원문의 정확한 문자열, `suggestion`에 정확한 대체 문자열만 넣는다. 문장 재작성이나 맥락 판단이 필요하면 설명형 제안으로 작성해 수동 수정 대상으로 구분한다.

하위 에이전트 응답이 유효한 JSON인지 필수 필드가 모두 있는지 확인한다. 잘못된 응답은 한 번만 수정 요청하고, 다시 실패하면 정확한 사유와 함께 해당 검사를 생략한다.

동일한 위반만 중복 제거하고 줄 번호(`null`은 마지막), 규칙 ID 순서로 정렬한다. 병합된 목록에서 심각도별 건수를 다시 계산한다.

### 4단계 — 보고서 출력 및 JSON 저장

파일별로 다음 형식의 한국어 보고서를 출력한다.

```markdown
## 번역 검토 결과: `파일경로`

### 위반 사항 (N개)

| 줄 | 규칙 ID | 심각도 | 위반 내용 | 수정 제안 |
|---:|---|---|---|---|

### 통과·생략 항목
- WIKI: ...
- KIGO: ...
- CUSTOM: ...
- SPELL: ...

### 총평
필수·권고·참고 항목 수와 우선순위를 간략히 설명합니다.
```

심각도는 `🔴 필수`, `🟡 권고`, `⚪ 참고`로 표시하고 표 셀을 깨뜨리는 문자는 이스케이프한다.

보고서 출력 직후 대상 파일 옆에 `<원본파일명>_validation.json`을 저장하고 절대 경로를 출력한다. 검증 JSON 저장은 검증 절차의 일부이며 번역 원문 수정 권한을 뜻하지 않는다.

```json
{
  "meta": {
    "validated_file": "/absolute/path/to/article.md",
    "validated_at": "2026-05-09T10:22:55Z",
    "summary": {
      "total": 0,
      "required": 0,
      "recommended": 0,
      "info": 0
    }
  },
  "violations": [
    {
      "line": 1,
      "rule_id": "WIKI-N",
      "source": "wiki",
      "problem": "위반 내용",
      "suggestion": "수정 제안",
      "severity": "required"
    }
  ],
  "passed": {
    "wiki": [],
    "kigo": [],
    "custom": [],
    "spell": []
  },
  "omitted": {}
}
```

UTC ISO 8601 타임스탬프를 사용한다. 네 검사가 모두 완료되면 `omitted` 키를 생략하고, 그렇지 않으면 생략한 `source`와 오류 원문을 기록한다.

### 5단계 — 자동 수정 선택

모든 대상의 보고서와 JSON 저장이 끝나면 다음 선택지를 제시한다.

1. **필수 항목만 수정** — 맞춤법과 명백한 필수 위반 중 안전한 항목만 적용
2. **필수 + 권고 항목 수정** — 안전한 권고 항목까지 적용
3. **건너뛰기** — 번역 원문을 변경하지 않음

사용자가 1번이나 2번을 선택하기 전에는 번역 원문을 수정하지 않는다. 검증 요청만으로 수정 권한을 추정하지 않는다.

수정 권한을 받으면 다음 절차를 따른다.

1. 원문과 저장된 JSON을 다시 읽는다.
2. 각 위반을 자동 적용, 수동 수정 필요, 건너뜀으로 분류한다.
3. 제외 범위 밖에서 `problem`이 유일하게 일치하고 치환이 명확한 항목만 한 번에 하나씩 수정한 뒤 문맥을 다시 확인한다.
4. 같은 줄의 여러 수정은 뒤쪽 항목부터 적용한다.
5. 문장 재작성, 중복 일치, `info`, 기술적 의미를 바꿀 가능성이 있는 변경은 수동 제안으로 남긴다.
6. 적용·수동 수정 필요·건너뜀 결과를 별도 표로 보고한다.
7. 수정된 파일에 네 검사를 다시 실행한다.
8. JSON의 결과, 통과·생략 정보, 타임스탬프, 통계를 재검증 결과로 교체하고 `meta.auto_fix`에 수정 기록을 남긴다.

```json
{
  "applied_at": "<UTC ISO 8601 timestamp>",
  "mode": "required_only | required_and_recommended",
  "applied": 0,
  "skipped": 0,
  "manual_required": 0
}
```

`applied`는 실제로 파일에 반영한 고유 치환 횟수로 센다. 같은 치환으로 여러 규칙의 중복 위반이 해결돼도 한 건으로 계산한다. 파일 변경과 수정 문맥을 확인하지 않은 항목은 적용했다고 보고하지 않는다.
