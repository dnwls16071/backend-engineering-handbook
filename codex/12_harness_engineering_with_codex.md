# Codex 하네스 엔지니어링

## 1. 프로젝트 규칙을 읽고 검증할 수 있는 환경을 만든다

하네스 엔지니어링은 Codex가 작업에 필요한 문서와 도구를 읽고, 정해진 범위에서 변경하고, 결과를 검증할 수 있도록 환경을 설계하는 일이다. OpenAI의 사례에서는 짧은 `AGENTS.md`를 저장소 문서의 안내판으로 사용하고, 반복되는 실패를 근거로 문서·도구·검증을 보완했다. [OpenAI 하네스 엔지니어링 사례](https://openai.com/index/harness-engineering/)

- **알려 주기.** `AGENTS.md`에 도메인 규칙, 작업 범위, 검증 명령을 적는다. 예를 들어 결제 작업의 규칙으로 같은 주문의 중복 결제 방지와 테스트 결제 환경 사용을 명시한다. [Codex의 `AGENTS.md` 가이드](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- **막기.** `PreToolUse` 훅은 지원하는 도구 호출을 실행 전에 차단할 수 있다. 테스트 수정 방지 훅을 만들 때는 `apply_patch`와 셸 편집을 각각 시험한다. [Codex의 `PreToolUse`와 도구 적용 범위](https://learn.chatgpt.com/docs/hooks)
- **권한 제한.** 샌드박스와 승인 정책으로 파일·네트워크 접근을 제한한다. 결제 실습에서는 테스트 자격 증명만 작업 환경에 제공한다. [Codex 승인과 샌드박스](https://learn.chatgpt.com/docs/agent-approvals-security)
- **확인하기.** `Stop` 훅으로 Codex가 턴을 마치려 할 때 관련 테스트를 실행한다. 실패 이유를 전달해 작업을 이어가게 할 수 있다. 같은 실패를 반복하면 추가 실행을 제한하고 마지막 실패를 남긴다. [Codex `Stop` 훅](https://learn.chatgpt.com/docs/hooks#stop)
- **되돌리기.** Git 작업 브랜치나 워크트리에 변경을 격리해 diff를 확인하고, 문제가 생기면 영향을 받은 변경을 찾아 되돌린다. [Git 워크트리 문서](https://git-scm.com/docs/git-worktree)

## 2. 같은 요청으로 하네스를 점검한다

같은 코드 상태와 요청으로 적용 전후를 비교한다. 보호 대상 파일의 diff, 테스트 실행 로그, 작업 중단 이유를 남긴다. 화면을 바꿨다면 같은 사용자 행동을 브라우저에서 재현하고 전후 결과를 확인한다. 규칙이 빠졌거나 정상 작업이 막혔다면 지침이나 훅을 고치고 같은 사례로 다시 점검한다. [OpenAI의 화면 검증과 피드백 사례](https://openai.com/index/harness-engineering/)
