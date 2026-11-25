# Codex 루프 엔지니어링

## 1. 수정·검증·재시도를 반복할 흐름을 정한다

루프 엔지니어링은 Codex가 변경한 결과를 테스트나 다른 검증 도구로 확인하고, 남은 실패를 다음 회차의 입력으로 돌려보내는 작업 흐름을 설계하는 일이다. [OpenAI의 Codex 반복 수정 예제](https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex)

- **하네스**로 저장소 지침, 실행 권한, 검증 도구를 마련해 각 회차의 작업 환경을 정한다. [OpenAI 하네스 사례](https://openai.com/index/harness-engineering/)
- **`/goal`**에 원하는 결과, 제약, 검증 기준을 적으면 Codex가 현재 대화에서 목표를 향해 작업을 이어간다. [Codex 장기 작업과 `/goal`](https://learn.chatgpt.com/docs/long-running-work)
- **`scripts/loop.sh` 같은 프로젝트 스크립트**에서는 `codex exec`를 비대화형으로 호출할 수 있다. 스크립트가 테스트를 실행하고 결과를 받아 다음 회차를 시작할지 결정한다. [Codex 비대화형 실행](https://learn.chatgpt.com/docs/non-interactive-mode)

## 2. 테스트 작성과 구현을 나누고 멈춤 조건을 정한다

- **테스트 작성.** 인수 조건을 테스트로 옮기고, 구현 전 예상한 이유로 실패하는지 확인한다. 구현 단계로 전환하면 같은 테스트의 기대값으로 수정 결과를 검증하고, 계약 자체를 바꿔야 하면 그 변경을 검토한다. [Martin Fowler의 테스트 주도 개발](https://martinfowler.com/bliki/TestDrivenDevelopment.html) · [위키 · 테스트 실패와 요구사항 변경](../test-driven-development/04_test_failures_and_safe_design_changes.md)
- **다음 회차.** 실패한 테스트 이름, 예상값과 실제값, 관련 로그를 Codex에 넘긴다. 화면 작업은 같은 사용자 흐름을 브라우저에서 재현한 결과도 남길 수 있다. [OpenAI의 반복 검증 예제](https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex) · [OpenAI의 화면 검증 사례](https://openai.com/index/harness-engineering/)
- **종료.** 필수 검사에 모두 통과하면 성공으로 끝낸다. 반복 상한에 도달하거나 실패가 줄지 않거나 사람의 결정이 필요하면 중단하고, 마지막 검증 결과와 diff를 남긴다. [OpenAI의 종료 조건과 실행 기록](https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex#generalize-to-a-continuous-loop)

## 3. 예약 앱에 적용한 인수 조건 예시

```text
결제 | 같은 결제 요청을 재시도해도 중복 승인되지 않는다.
결제 응답 유실 | 기존 결제 시도의 결과를 조회한 뒤 예약 상태를 반영한다.
노쇼·대기자 승계 | 노쇼 처리 조건을 충족하면 대기자 한 명을 승계한다.
중복 처리 | 같은 노쇼 처리를 두 번 실행해도 추가 승계가 발생하지 않는다.
브라우저 확인 | 지도에서 예약 대상을 선택해 테스트 결제까지 진행한다.
브라우저 확인 | 노쇼 처리 후 예약자와 승계된 대기자 화면에서 각 상태를 확인한다.
리뷰 | 상태 전이, 회귀 테스트 실행 결과, 변경 diff를 함께 확인한다.
```

응답 유실을 재현할 때는 승인 직후 연결이 끊긴 경우와 호출 전에 실패한 경우를 분리하고, 재시도 뒤 승인 건수와 내부 상태 반영 횟수를 확인한다. [AWS 멱등 재시도 설계](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [위키 · 결제 재시도 테스트](../payment-system/03_confirming_payments_with_idempotency_retries_and_timeouts.md)
