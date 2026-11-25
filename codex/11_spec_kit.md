# Spec Kit로 명세 주도 개발하기

## 1. 요구사항에서 구현에 필요한 문서를 차례로 만든다

GitHub Spec Kit은 기능의 목표와 사용자 요구사항을 먼저 정리하고, 이를 바탕으로 기술 계획과 작업 목록을 만들어 구현까지 이어가는 도구다. 프로젝트 초기에 `constitution`으로 테스트 기준과 호환성 정책처럼 프로젝트 전체에 적용할 원칙을 정한다. [Spec Kit 빠른 시작](https://github.github.io/spec-kit/quickstart.html)

- `specify`는 `spec.md`에 기능의 목표, 사용자 시나리오, 요구사항과 검증 가능한 인수 조건을 정리한다. 계획 전에 `clarify`를 실행하면 남은 모호함을 질문으로 확인해 명세에 반영한다. [Spec Kit 명세와 명확화](https://github.github.io/spec-kit/reference/agentic-sdd.html)
- `plan`은 `plan.md`에 기술 선택과 구현 설계를 구체화한다. `checklist`를 실행하면 요구사항 자체의 명확성과 완전성을 검토할 목록을 만들 수 있다. [Spec Kit 계획과 체크리스트](https://github.github.io/spec-kit/reference/agentic-sdd.html)
- `tasks`는 설계를 실행 가능한 작업으로 나누고 의존 순서를 반영해 `tasks.md`에 기록한다. `analyze`는 구현 전에 `spec.md`, `plan.md`, `tasks.md` 사이의 충돌과 누락을 읽기 전용으로 점검한다. [Spec Kit 작업 목록과 분석](https://github.github.io/spec-kit/reference/agentic-sdd.html)

## 2. 작업 목록에 따라 구현하고 결과를 명세와 대조한다

- `implement`는 `tasks.md`에 따라 작업을 수행한다. `converge`는 구현 결과를 명세·계획·작업 목록과 대조하고 빠진 작업이 있으면 `tasks.md`에 추가한다. [Spec Kit 구현과 검증](https://github.github.io/spec-kit/reference/agentic-sdd.html)
- 공식 빠른 시작의 짧은 흐름은 `specify` → `plan` → `tasks` → `implement` → `converge`다. 요구사항이 복잡하면 `clarify`, `checklist`, `analyze`를 해당 단계에 추가할 수 있다. [Spec Kit 공식 권장 흐름](https://github.github.io/spec-kit/quickstart.html)
