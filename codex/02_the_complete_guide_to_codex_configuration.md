# Codex 설정: config.toml로 실행 환경과 동작 제어하기

## 1. 설정으로 작업 방식과 실행 범위를 정한다

- **Codex 설정은 모델 선택뿐 아니라 승인 요청, 샌드박스, 웹 검색과 외부 도구 연동 등 작업 전반의 동작을 제어한다.**
- 사용자 공통 설정과 프로젝트별 설정을 나누면 개인의 기본 작업 방식과 프로젝트 요구사항을 함께 반영할 수 있다.
- MCP와 훅 같은 확장 기능도 설정의 대상이다.
- 기본 실행 범위와 승인 정책을 먼저 정하고, 필요한 기능을 점진적으로 추가한다.

## 2. 설정 파일의 위치와 적용 우선순위를 이해한다

| 범위 | 파일 위치 | 용도 |
| :--- | :--- | :--- |
| 사용자 | `~/.codex/config.toml` | 사용자에게 공통으로 적용할 설정 |
| 프로젝트 | `.codex/config.toml` | 프로젝트별 설정 |
| 시스템 | `/etc/codex/config.toml` | 시스템 차원의 설정 |

- **프로젝트 설정은 신뢰된 프로젝트에서만 로드된다.**
- 같은 설정 항목이 여러 곳에 있으면 다음 순서에서 위에 있는 값이 우선한다.

1. CLI 플래그와 `--config`로 지정한 값
2. `--profile <name>`으로 선택한 프로필의 값
3. 프로젝트의 `.codex/config.toml`
4. 사용자의 `~/.codex/config.toml`
5. 시스템의 `/etc/codex/config.toml`
6. 내장 기본값

- 설정을 바꿨는데 동작이 달라지지 않으면 더 높은 우선순위에서 같은 항목을 지정했는지 확인한다.

## 3. 기본 설정 항목을 구분한다

```toml
model = "gpt-5.5"
approval_policy = "on-request"
sandbox_mode = "workspace-write"
web_search = "cached"
model_reasoning_effort = "high"
personality = "friendly"
```

| 항목 | 역할 | 설정값 예시 |
| :--- | :--- | :--- |
| `model` | 사용할 모델 선택 | `"gpt-5.5"` |
| `approval_policy` | 명령 실행 전 승인 요청 방식 | `"untrusted"`, `"on-request"`, `"never"` |
| `sandbox_mode` | 파일시스템과 네트워크 접근 범위 | `"read-only"`, `"workspace-write"`, `"danger-full-access"` |
| `web_search` | 웹 검색 방식 | `"cached"`, `"live"`, `"disabled"` |
| `model_reasoning_effort` | 모델의 추론 노력 수준 | `"low"`, `"medium"`, `"high"` |
| `personality` | 응답 스타일 | `"friendly"`, `"pragmatic"`, `"none"` |

## 4. 승인 정책과 샌드박스를 따로 설정한다

- **승인 정책은 언제 사용자에게 물을지를, 샌드박스는 어떤 범위에서 실행할 수 있는지를 정한다.**

| 승인 정책 | 동작 |
| :--- | :--- |
| `untrusted` | 신뢰되지 않은 명령에 대해 승인을 요청한다. |
| `on-request` | Codex가 필요하다고 판단할 때 승인을 요청한다. |
| `never` | 실행 전 사용자 승인을 요청하지 않는다. |

- 승인 정책은 필요에 따라 더 세분화해 설정할 수도 있다.

| 샌드박스 모드 | 실행 범위 |
| :--- | :--- |
| `read-only` | 파일 읽기를 허용하고 쓰기를 제한한다. |
| `workspace-write` | 작업 공간 내 쓰기를 허용한다. |
| `danger-full-access` | 샌드박스의 접근 제한을 해제한다. |

- 일반적인 작업은 `workspace-write`를 출발점으로 삼고 필요한 접근 범위를 조정한다.

### 작업 공간 쓰기 모드의 세부 설정

```toml
[sandbox_workspace_write]
network_access = false
writable_roots = ["/Users/YOU/.pyenv/shims"]
exclude_tmpdir_env_var = false
exclude_slash_tmp = false
```

- `network_access`는 네트워크 접근 허용 여부를 제어한다.
- `writable_roots`에는 추가로 쓰기를 허용할 경로를 지정한다.
- `exclude_tmpdir_env_var`는 `TMPDIR` 환경 변수가 가리키는 임시 디렉터리를 쓰기 허용 대상에서 제외할지 정한다.
- `exclude_slash_tmp`는 `/tmp`를 쓰기 허용 대상에서 제외할지 정한다.
- 두 제외 옵션을 `false`로 두면 해당 임시 디렉터리를 제외하지 않는다.

## 5. 웹 검색의 범위를 선택한다

| 모드 | 동작 |
| :--- | :--- |
| `cached` | 기본적으로 캐시된 검색 결과를 사용한다. |
| `live` | 최신 데이터를 가져온다. |
| `disabled` | 웹 검색을 사용하지 않는다. |

- **검색 방식과 관계없이 웹 결과는 신뢰되지 않은 외부 입력으로 취급한다.**

## 6. 프로필과 CLI 옵션으로 상황별 설정을 적용한다

- 프로필은 작업 목적에 맞는 설정 묶음이다.
- `[profiles.<name>]`에 값을 정의하고 `--profile <name>`으로 선택한다.

```toml
[profiles.deep-review]
model = "gpt-5-pro"
model_reasoning_effort = "high"
approval_policy = "never"

[profiles.lightweight]
model = "gpt-4.1"
approval_policy = "untrusted"
```

```sh
codex --profile deep-review
```

- 일회성 변경은 설정 파일을 수정하지 않고 CLI 옵션으로 적용한다.
- 중첩된 설정 항목은 점으로 연결한 키로 지정할 수 있다.

```sh
codex --model gpt-5.4
codex --config 'model="gpt-5.4"'
codex --config sandbox_workspace_write.network_access=true
codex --config 'shell_environment_policy.include_only=["PATH","HOME"]'
```

## 7. 셸에 전달할 환경 변수를 제한한다

```toml
[shell_environment_policy]
include_only = ["PATH", "HOME"]
```

- `include_only`로 셸 실행 환경에 전달할 환경 변수의 허용 목록을 지정한다.
- 위 설정은 `PATH`와 `HOME`을 전달하도록 범위를 제한한다.

## 8. 사용자 정의 모델 공급자를 연결한다

```toml
model = "gpt-5.4"
model_provider = "proxy"

[model_providers.proxy]
name = "OpenAI using LLM proxy"
base_url = "https://proxy.example.com/v1"
env_key = "OPENAI_API_KEY"
```

- `model_provider`는 사용할 공급자의 식별자이며, 대응하는 `[model_providers.<name>]`에 연결 정보를 정의한다.
- `base_url`에는 API 엔드포인트를, `env_key`에는 인증 키를 읽어 올 환경 변수 이름을 지정한다.
- 프록시 같은 사용자 정의 연결 경로를 설정해 모델 호출에 사용할 수 있다.

## 9. 훅으로 도구 실행 전 검사를 추가한다

```toml
[[hooks.PreToolUse]]
matcher = "^Bash$"

[[hooks.PreToolUse.hooks]]
type = "command"
command = "/usr/bin/python3 ./policy.py"
timeout = 30
statusMessage = "Checking Bash command"
```

- `PreToolUse` 훅은 도구 실행 전에 동작한다.
- `matcher`로 적용 대상을 지정하며, `^Bash$`는 이름이 `Bash`인 도구와 일치한다.
- 실행할 명령, 제한 시간과 상태 메시지를 설정해 도구 사용 전에 정책 검사를 추가할 수 있다.

## 10. 기본 운영 설정을 구성한다

```toml
model = "gpt-5.5"
approval_policy = "on-request"
sandbox_mode = "workspace-write"
web_search = "cached"
model_reasoning_effort = "high"

[shell_environment_policy]
include_only = ["PATH", "HOME"]

[sandbox_workspace_write]
network_access = false
```

- 승인 요청을 허용하면서 작업 공간 안에서 파일을 수정하고, 네트워크 접근은 제한하는 구성이다.
- 작업 목적에 따른 차이는 프로필로 관리하고, 일회성 변경은 CLI 옵션으로 적용한다.
- **설정을 이해할 때는 값 자체와 함께 적용 범위, 우선순위, 승인 방식과 실행 권한을 확인한다.**
