# Plugins: Skills와 외부 연동을 설치 가능한 확장으로 배포하기

## 1. 재사용할 기능을 설치 가능한 단위로 묶는다

- **플러그인은 Codex의 기능을 확장하는 설치 가능한 패키지이다.**
- Skills, MCP 서버와 앱 연동을 함께 포함할 수 있다.
- 개인이 만든 작업 방식과 연동을 다른 사용자나 팀에서도 재사용할 수 있도록 배포한다.
- 팀의 공통 워크플로를 각 구성원이 개별적으로 구성하는 부담을 줄일 수 있다.

## 2. Skill과 플러그인의 책임을 구분한다

| 구분 | Skill | 플러그인 |
| :--- | :--- | :--- |
| 중심 역할 | 특정 작업의 절차와 지침 정의 | 여러 기능을 묶어 설치·배포 |
| 주요 구성 | 작업별 실행 지침과 재사용할 워크플로 | Skills, MCP 서버와 앱 연동 |
| 활용 목적 | 같은 작업을 일관된 방식으로 수행 | 관련 기능과 연결을 사용자·팀에 제공 |

- Skill은 개별 워크플로에 집중하고, 플러그인은 이를 외부 연동과 함께 제공할 수 있다.
- **작업 방법을 정의하는 단위와 기능을 배포하는 단위를 구분해 설계한다.**

## 3. 앱이나 CLI에서 플러그인을 설치한다

Codex 앱에서는 다음 순서로 설치한다.

1. Plugin Directory를 연다.
2. 사용할 플러그인을 찾아본다.
3. Install을 선택한다.
4. Codex에 추가한다.

- CLI에서는 `/plugins`로 플러그인 관리 화면에 접근한다.

## 4. 매니페스트를 중심으로 파일을 구성한다

```text
my-plugin/
├── .codex-plugin/
│   └── plugin.json
├── skills/
│   └── my-skill/
├── hooks/
│   └── hooks.json
├── .app.json
├── .mcp.json
└── assets/
```

| 구성요소 | 역할 |
| :--- | :--- |
| `.codex-plugin/plugin.json` | 플러그인을 정의하는 필수 매니페스트 |
| `skills/` | 플러그인에 포함할 Skills |
| `hooks/hooks.json` | 수명주기 이벤트에 연결할 훅 설정 |
| `.app.json` | 앱과 커넥터 매핑 |
| `.mcp.json` | MCP 서버 설정 |
| `assets/` | 아이콘, 로고와 스크린샷 |

- **`plugin.json`을 중심으로 필요한 기능의 경로와 정보를 연결한다.**
- 훅, 앱 매핑, MCP 설정과 시각 자료는 제공할 기능에 따라 추가한다.

## 5. plugin.json에 메타데이터와 기능 경로를 선언한다

```json
{
  "name": "my-first-plugin",
  "version": "0.1.0",
  "description": "My First Plugin plugin",
  "author": {
    "name": "Local developer"
  },
  "skills": "./skills/",
  "hooks": "./hooks/hooks.json",
  "mcpServers": "./.mcp.json",
  "interface": {
    "displayName": "My First Plugin",
    "category": "Productivity",
    "capabilities": ["MCP", "Tools"]
  }
}
```

- 이름, 버전, 설명과 작성자 정보로 플러그인을 식별한다.
- `skills`, `hooks`와 `mcpServers`로 포함할 기능의 설정 경로를 지정한다.
- `interface`에는 표시 이름, 카테고리와 제공 기능 등 사용자에게 보여 줄 정보를 담는다.
- 배포 시에는 플러그인 정보와 함께 설치 정책, 인증 정책과 패키지 위치도 관리한다.

## 6. 로컬에서 개발하고 마켓플레이스에 등록한다

- 내장 `$plugin-creator`를 활용하거나 파일을 직접 작성해 로컬 플러그인을 만들 수 있다.
- 마켓플레이스에는 플러그인의 이름, 위치와 설치·인증 정책을 등록한다.

```json
{
  "name": "learn-codex",
  "interface": {
    "displayName": "Learn Codex"
  },
  "plugins": [
    {
      "name": "my-first-plugin",
      "source": {
        "source": "local",
        "path": "./plugins/my-first-plugin"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
```

- 위 구성은 로컬 경로에 있는 플러그인을 마켓플레이스에 등록하는 예시이다.
- `source`에는 패키지 위치를, `policy`에는 설치와 인증 정책을 지정한다.
- 저장소 기반 마켓플레이스와 개인 마켓플레이스를 활용해 공유 범위를 구성할 수 있다.

## 7. 캐시 위치를 이해하고 팀에 배포한다

- 플러그인 캐시는 다음과 같이 마켓플레이스, 플러그인과 버전별 경로로 구분된다.

```text
~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/
```

- 팀 배포는 개발자가 플러그인을 마켓플레이스에 게시하고, 다른 구성원이 설치해 자신의 프로젝트에서 사용하는 흐름이다.
- **팀의 Skills와 연동을 하나의 배포 단위로 제공해 공통 작업 방식을 공유할 수 있다.**
- 플러그인 구성, 마켓플레이스 등록과 설치를 연결해 워크플로를 재사용한다.
