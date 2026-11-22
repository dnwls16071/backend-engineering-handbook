# Lounge Wiki Workflow

`lounge`의 주제별 Markdown은 다른 업무 프로젝트를 구현할 때도 검색할 수 있다. `lounge` 자체를 열었을 때는 저장소의 `AGENTS.md`가 위키 관리 방법을 안내한다. 로컬 검색과 검증에는 Python 3.9 이상과 Git이 필요하다.

## 1. 업무 프로젝트를 구현하면서 위키 참고하기

Codex를 **구현할 업무 저장소**에서 열고 기능이나 수정 사항을 요청한다. Codex는 현재 프로젝트의 코드, 의존성 버전, 테스트를 확인한다. 설계나 운영 판단에 관련된 `lounge` 문서를 찾아 읽고, 사용할 API와 동작 조건은 Context7에서 해당 버전의 공식 문서로 대조한다. 확인한 내용을 바탕으로 현재 프로젝트에 맞게 구현하고 테스트한다.

> 결제 API의 타임아웃 재시도에서 중복 결제를 막도록 구현해 줘. 먼저 이 프로젝트의 결제 처리와 테스트를 읽고, `lounge`에서 멱등 키와 커밋 응답 유실 사례를 찾아 설계에 참고해. 사용할 Spring·DB 동작은 이 프로젝트 버전의 공식 문서를 Context7에서 확인해. 구현과 검증은 이 업무 저장소에서 진행해 줘.

같은 흐름을 매번 요청하고 싶지 않다면 업무 저장소의 `AGENTS.md`에 아래 지침을 추가한다. 로컬 체크아웃 위치가 다르면 `lounge` 경로를 바꾼다.

```md
## 구현 작업에서 기술 자료 확인하기

- 먼저 이 프로젝트의 기존 코드, 테스트, 실제 의존성 버전과 설정을 확인한다.
- 설계 결정이나 장애 대응에 관련된 사례가 필요하면 `python3 /Users/jwj/Desktop/lounge/wiki/wiki.py search "검색어" --limit 8`로 위키를 검색하고, 관련 결과의 앞뒤 문맥을 읽는다. 주제가 명확하면 `--scope <주제 폴더>`를 사용한다.
- 사용할 외부 API나 제품 동작과 제약은 이 프로젝트가 사용하는 버전의 공식 문서를 Context7에서 찾아 확인한다. 문의에는 공개 기술 용어만 사용한다.
- 확인한 설계와 API를 이 프로젝트의 코드와 테스트에 반영한다. 중요한 판단에 참고한 위키 경로와 공식 근거를 작업 결과에 남긴다.
- 업무 코드 변경의 리뷰는 요청할 때 이 업무 저장소의 CodeRabbit 절차를 따른다. 위키에서 오류를 발견하면 문서 경로와 근거를 보고하고, 위키 수정이 요청되면 별도로 반영한다.
```

위키 파일을 복사하거나 업무 저장소에 추가할 필요 없이 외부 경로로 읽을 수 있다. 예를 들어 어느 디렉터리에서든 다음 명령으로 Aurora MySQL 노트를 검색한다.

```bash
python3 /Users/jwj/Desktop/lounge/wiki/wiki.py search '멱등' --scope aurora-mysql --limit 3
```

## 2. 위키를 검색하고 공식 원문으로 확인하기

```bash
python3 wiki/wiki.py search 'SKIP LOCKED' --scope mysql --limit 8
python3 wiki/wiki.py check --scope mysql
```

Codex에 다음과 같이 요청한다.

> `mysql` 위키에서 `SKIP LOCKED`의 사용 조건을 찾아 줘. Context7에서 해당 MySQL 버전의 공식 문서를 찾고, 공식 원문과 다른 부분이 있으면 해당 문서만 고쳐 줘. 확인한 근거와 남은 의문을 경로와 줄 번호로 알려 줘.

Context7에는 라이브러리 이름, 버전, 확인할 공개 API나 동작을 보낸다. 기술 내용을 고치기 전에 공식 원문을 열어 새 주장을 뒷받침하는 부분과 적용 조건을 대조한다. 다른 버전이나 API의 자료만 나오면 해당 버전의 공식 매뉴얼에서 직접 확인한다. 근거가 부족한 주장은 본문을 유지하고 확인 필요 항목으로 남긴다.

## 3. 주장과 원문 위치 기록하기

검증한 핵심 주장 옆에 공식 출처 링크를 붙이고 [근거 목록](evidence.json)에 한 건씩 등록한다.

| 필드 | 저장할 내용 |
| --- | --- |
| `page` | 저장소 루트 기준 위키 문서 경로 |
| `claim` | 위키에서 확인한 한 줄 전체. 목록 기호와 Markdown 서식 포함 |
| `applies_to` | 제품 버전, 동작 모드, 환경 등 해당 주장의 적용 범위 |
| `checked_on` | 원문을 대조한 날짜. `YYYY-MM-DD` |
| `source.url`, `source.locator` | 공식 HTTPS 주소와 제목, 절 또는 표의 위치 |
| `source.path`, `source.start`, `source.end`, `source.quote` | 로컬 원문을 인용할 때 사용하는 상대 경로, 1부터 시작하는 양끝 포함 줄 번호, 정확한 발췌 |

외부 주소와 로컬 발췌 중 하나를 `source`에 넣는다. 로컬 원문에서 비밀과 개인정보를 제외한 짧은 구절만 저장한다. 문서나 원문이 바뀌었다는 결과가 나오면 두 원문을 다시 대조한 다음 주장과 근거를 함께 갱신한다. `pages_with_evidence`는 적어도 한 건이 등록된 문서 수다. 등록되지 않은 주장은 따로 확인해야 한다.

## 4. 위키 변경을 검증하고 리뷰하기

```bash
python3 wiki/wiki.py check --changed --scope mysql
python3 wiki/wiki.py check --scope mysql/11_locking_reads_with_skip_locked.md --require-evidence
python3 wiki/wiki.py review --preview mysql
python3 wiki/wiki.py review mysql
```

`check`는 번호가 붙은 `##` 제목의 순서, 일반 코드 펜스, 인라인 상대 경로의 파일 존재, 등록된 주장과 로컬 인용을 검사한다. 외부 원문은 Codex가 확인하며 로컬 검사기는 원문의 주소와 위치 기록을 검사한다. `--changed`는 작업 트리와 스테이징 영역의 변경을 합쳐 본다. `--json`은 스크립트에서 결과를 읽을 때 사용할 수 있다. 종료 코드 `1`은 점검 항목 발견, `2`는 입력 또는 실행 오류다.

기술 내용을 고친 뒤에는 문서마다 `--require-evidence`를 실행한다. 이 옵션은 마지막 커밋과 작업 트리를 비교해 추가하거나 바꾼 본문 줄에 일치하는 근거가 없으면 실패한다. 제목, 서식 구분 줄, 코드 펜스는 검사 대상에서 제외한다. 삭제한 문장과 바꾼 코드 예제가 적절한지는 공식 원문과 diff를 대조해 확인한다. 서식만 수정했으면 기본 `check`를 사용한다.

`review`는 지정한 주제의 미커밋 Markdown 변경을 CodeRabbit에 보내고 루트의 `AGENTS.md`를 리뷰 지침으로 사용한다. `--preview`로 대상 경로를 확인할 수 있고, Git에 추가하지 않은 새 문서는 `--include-untracked`로 포함한다. 인증 상태는 `coderabbit auth status --agent`로 확인한다. 리뷰에서 나온 사실 관계는 해당 버전의 공식 원문을 확인해 반영하고 `check`를 다시 실행한다. [CodeRabbit CLI 명령](https://docs.coderabbit.ai/cli/reference#review)

## 5. 오래된 근거 다시 확인하기

```bash
python3 wiki/wiki.py check --scope mysql --max-age 90
```

예시의 90일은 작업자가 정하는 재확인 주기다. `recheck` 항목부터 공식 원문을 다시 확인하고, 주장의 의미와 조건을 확인한 날에만 `checked_on`을 갱신한다. 적용 범위가 일치하는데 원문끼리 상충하면 어느 근거가 충돌했는지와 지금 확인할 수 있는 범위를 적는다.

## 6. Codex 종료 시 자동 점검 연결하기

[프로젝트 훅 예시](codex-hooks.json)의 `Stop` 항목을 저장소의 `.codex/hooks.json`에 추가한다. 기존 설정이 있으면 `hooks.Stop` 항목에 병합한다. Codex CLI를 저장소에서 연 뒤 `/hooks`에서 정의를 검토하고 신뢰한다. 훅은 현재 Git 변경의 로컬 점검 결과에 문제가 있으면 경고를 표시한다. 검색, 검증, 리뷰는 훅을 등록하기 전에도 직접 실행할 수 있다. [Codex Hooks 공식 문서](https://learn.chatgpt.com/docs/hooks)

## 7. 검색과 LLM 답변의 회귀 확인하기

[기본 평가셋](evaluation-cases.json)은 15개 질문으로 근거를 찾을 수 있는 사례 13건과 답변 보류 사례 2건을 검사한다. 각 질문의 `query`와 `scope`로 기존 위키 검색을 실행하고, 파일별 첫 결과를 기준으로 상위 5개 문서에 기대 경로가 있는지 확인한다. 기본 실행은 첫 검색 결과의 한 줄을 답변으로 사용한다.

```bash
python3 -B wiki/evaluate.py run --out /tmp/lounge-before.json
# 위키 문서나 검색을 변경한 뒤 실행
python3 -B wiki/evaluate.py run --out /tmp/lounge-after.json
python3 -B wiki/evaluate.py compare /tmp/lounge-before.json /tmp/lounge-after.json
```

비교는 같은 평가셋, 검색 개수, 답변 모드로 실행한 보고서를 사용한다. 질문별로 새로 실패한 검사, 해결된 검사, 계속 실패하는 검사를 출력한다. JSON 보고서에는 검색된 문서와 줄, 검증된 인용 위치, 실패 사유가 남는다. `run`은 실패한 질문이 있으면 코드 1을 반환하고, `compare`는 새로 실패한 검사가 있으면 코드 1을 반환한다. 입력 또는 실행 오류는 코드 2다.

실제 답변을 평가할 때는 질문 목록을 내보낸다. Codex에 각 질문을 위키 문서로 답하고, 결과를 아래 형식의 JSON 객체에 질문 ID별로 저장하도록 요청한다. 기준과 후보 답변을 각각 만든 뒤 같은 평가셋으로 채점한다.

```bash
python3 -B wiki/evaluate.py questions > /tmp/lounge-questions.json
python3 -B wiki/evaluate.py run --answers /tmp/lounge-answers-before.json --out /tmp/lounge-llm-before.json
python3 -B wiki/evaluate.py run --answers /tmp/lounge-answers-after.json --out /tmp/lounge-llm-after.json
python3 -B wiki/evaluate.py compare /tmp/lounge-llm-before.json /tmp/lounge-llm-after.json
```

다음은 답변 파일에서 한 질문에 해당하는 항목이다. 전체 실행에는 질문 목록의 모든 ID가 필요하다.

```json
{
  "postgres-serialization-retry": {
    "status": "answered",
    "answer": "SQLSTATE 40001을 받으면 트랜잭션 전체를 다시 실행합니다.",
    "citations": [
      {
        "path": "postgresql/05_postgresql_transactions_mvcc_and_hybrid_search.md",
        "line": 23,
        "quote": "직렬화 실패 SQLSTATE `40001`을 재시도할 때는 트랜잭션 전체를 다시 실행한다. 중간에 외부 시스템을 호출한다면 같은 요청을 재실행해도 부작용이 중복되지 않도록 설계한다."
      }
    ]
  }
}
```

인용은 저장소 상대 경로, 1부터 시작하는 줄 번호, 해당 Markdown 줄 전체를 사용한다. 위키에서 근거를 찾지 못했다면 `status`는 `insufficient_evidence`로 두고, `answer`에 이유를 적고, `citations`는 빈 배열로 둔다. 채점기는 기대 용어가 답변과 실제 인용에 있는지 검사한다. 문장이 같은 뜻인지, 인용이 답변의 모든 주장을 뒷받침하는지는 사람이 검토한다. 명령 자체는 모델을 호출하지 않는다.
