# Agent Skills로 PRD 작성, Figma UI 분석, 작업 인수인계하기

## 1. `PRD.md`에 제품 요구사항과 인수 조건을 적는다

GitHub `awesome-copilot`의 `prd` 스킬은 문제와 성공 기준을 확인한 뒤 사용자 흐름, 범위, 인수 조건을 정리한다. `PRD.md`에는 주요 사용자, 해결하려는 문제, 첫 출시 범위와 제외 범위, 성공·실패 시나리오를 기록한다. [GitHub PRD 스킬](https://github.com/github/awesome-copilot/blob/main/skills/prd/SKILL.md)

### 실시간 방명록의 인수 조건 예시

```text
첫 출시 범위 | 닉네임과 메시지 입력, 글 등록, 최신순 목록, 새 글 실시간 반영
정상 | 브라우저 A에서 새 글을 등록하면 브라우저 B의 목록 맨 위에 새로고침 없이 한 번 표시된다.
실패 | 등록에 실패하면 입력 내용이 유지되고 사용자가 다시 등록할 수 있다.
```

## 2. Figma 프레임에서 확인한 내용을 `DESIGN.md`에 옮긴다

분석 대상은 Figma의 프레임 또는 레이어 링크로 지정한다. `get_design_context`로 구조를 읽고 `get_screenshot`으로 화면을 대조한다. `get_variable_defs`로 선택 영역에서 쓰는 색상, 간격, 타이포그래피 변수와 스타일을 확인한다. [Figma MCP 도구](https://developers.figma.com/docs/figma-mcp-server/tools-and-prompts/) · [프레임 링크로 조회하기](https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/#example-get-design-context)

### `DESIGN.md` 구성 예시

```text
원본 | 분석한 Figma 프레임 링크
레이아웃 | 작성 폼과 메시지 목록의 배치, 프레임별 차이
토큰 | Figma에서 확인한 색상·간격·타이포그래피 변수명과 값
컴포넌트 | 입력 필드, 등록 버튼, 메시지 카드와 확인한 상태
확인 필요 | PRD에 있는 등록 실패 상태의 화면이 Figma에서 확인되지 않음
```

## 3. 메모리 뱅크 스킬에 작업 재개 절차를 적는다

Codex의 `$skill-creator`를 사용해 `memory-bank` 같은 재사용 워크플로를 정의할 수 있다. `SKILL.md`의 `description`에 사용 시점을 적고, 본문에는 읽을 파일과 갱신 절차를 둔다. [OpenAI 스킬 작성 가이드](https://developers.openai.com/plugins/build/skills) · [Agent Skills 명세](https://agentskills.io/specification)

### 메모리 뱅크 스킬과 작업 기록 예시

```text
SKILL.md | 작업 재개나 인수인계 요청에 사용한다.
시작 | memory-bank/status.md, 관련 PRD와 DESIGN.md를 읽고 현재 코드와 대조한다.
종료 | 완료 항목, 확정한 결정, 검증 결과, 남은 질문과 다음 작업을 status.md에 갱신한다.

status.md 기록 예시
완료 | 등록 실패 시 입력값 유지
검증 | 실패 응답을 재현하고 닉네임과 메시지가 폼에 남는 것을 확인
다음 | 두 브라우저에서 새 글이 한 번만 표시되는지 확인
```
