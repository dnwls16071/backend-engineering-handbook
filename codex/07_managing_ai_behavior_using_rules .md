# Rules: 명령 실행의 허용·승인·차단 정책 관리하기

## 1. 명령의 성격에 따라 실행 정책을 나눈다

- **Rules는 Codex가 실행하는 명령을 허용하거나, 사용자 승인을 요구하거나, 차단하는 실행 정책이다.**
- `pytest`, `git status`, `git push`와 `rm -rf`는 실행 목적과 영향이 다르므로 같은 기준으로 다루기 어렵다.
- 반복적인 검증 작업은 허용하고, 검토가 필요한 작업에는 승인을 요구하며, 허용하지 않을 작업은 차단할 수 있다.
- 실행 가능한 행동과 승인 시점을 규칙으로 명시해 에이전트의 작업 범위를 관리한다.

## 2. allow·prompt·deny로 실행 결정을 표현한다

| 결정 | 의미 |
| :--- | :--- |
| `allow` | 해당 규칙에 맞는 명령의 실행을 허용한다. |
| `prompt` | 실행 전에 사용자 승인을 요구한다. |
| `deny` | 해당 규칙에 맞는 명령의 실행을 차단한다. |

- **명령이 데이터를 읽기만 하더라도 팀 정책에 따라 승인을 요구할 수 있다.**
- 예를 들어 PR에는 내부 코드, 보안 논의, 고객 데이터와 아키텍처 정보가 포함될 수 있다.
- 작업의 변경 여부뿐 아니라 접근하는 정보의 성격도 승인 정책을 정하는 기준이다.

## 3. prefix_rule로 명령 접두사에 정책을 적용한다

```python
prefix_rule(
    pattern=["gh", "pr", "view"],
    decision="prompt",
    justification="Viewing PRs is allowed with approval",
)
```

| 항목 | 역할 |
| :--- | :--- |
| `pattern` | 매칭할 명령 접두사를 인자 목록으로 지정한다. |
| `decision` | 매칭되는 명령에 적용할 실행 결정을 정한다. |
| `justification` | 규칙의 이유, 보안 근거와 팀 정책을 설명한다. |

- 위 규칙은 `gh pr view`로 시작하는 명령에 사용자 승인을 요구한다.
- `gh pr view 123`이나 `gh pr view --repo my/repo`처럼 뒤에 인자가 추가되어도 접두사가 일치한다.
- `justification`을 남기면 규칙이 필요한 이유를 이해하고 검토할 수 있다.

## 4. match와 not_match로 적용 범위를 검증한다

```python
prefix_rule(
    pattern=["gh", "pr", "view"],
    decision="prompt",
    justification="Viewing PRs is allowed with approval",
    match=[
        "gh pr view 123",
    ],
    not_match=[
        "gh pr --repo x view 123",
    ],
)
```

- `match`에는 규칙과 일치해야 하는 명령 예시를 적는다.
- `not_match`에는 규칙과 일치하지 않아야 하는 명령 예시를 적는다.
- **두 항목은 규칙의 매칭 동작을 검증하기 위한 예시이다.**
- `gh pr --repo x view 123`은 PR을 조회하는 명령이어도 시작 인자 배열이 `gh pr view`와 다르다.
- 명령의 목적뿐 아니라 실제 인자 순서를 기준으로 적용 범위를 확인한다.

## 5. 파일로 저장하고 여러 규칙을 함께 관리한다

- Codex는 파일에서 Rules를 읽는다.
- 일반적인 저장 위치는 `~/.codex/rules/`이다.
- `github.rules`, `python.rules`처럼 용도에 따라 파일을 나눌 수 있다.
- 하나의 파일에 여러 규칙을 작성할 수도 있다.

```python
prefix_rule(
    pattern=["pytest"],
    decision="allow",
)

prefix_rule(
    pattern=["git", "push"],
    decision="prompt",
)

prefix_rule(
    pattern=["rm", "-rf"],
    decision="deny",
)
```

- 이 구성은 `pytest` 실행을 허용하고, `git push`에는 승인을 요구하며, `rm -rf` 접두사와 일치하는 명령을 차단한다.

## 6. execpolicy check로 실행 결정을 확인한다

```sh
codex execpolicy check --pretty \
  --rules ~/.codex/rules/default.rules \
  -- gh pr view 7888 --json title,body,comments
```

- `--rules`로 검사할 규칙 파일을 지정한다.
- `--` 뒤에는 정책을 확인할 명령과 인자를 전달한다.
- `--pretty`로 결과를 읽기 쉽게 출력한다.
- 규칙을 적용하기 전에 의도한 명령이 어떤 결정에 해당하는지 확인한다.

## 7. 팀의 작업 기준을 실행 정책으로 표현한다

| 정책 예시 | 명령 예시 |
| :--- | :--- |
| 허용 | `pytest`, `ruff`, `mypy` |
| 승인 요구 | `gh pr view`, `kubectl`, `terraform apply` |
| 차단 | `rm -rf`, `sudo` |

- 테스트·린트·타입 검사, 정보 조회, 인프라 변경과 권한 상승을 구분해 정책을 설계할 수 있다.
- 구체적인 허용 범위는 팀의 보안 요구사항과 작업 환경에 맞춰 정한다.
- **Rules는 명령 실행의 안전성, 권한과 사용자 승인 절차를 관리하는 장치이다.**
