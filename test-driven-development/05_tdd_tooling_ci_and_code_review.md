# TDD Tooling, CI, and Code Review

TDD의 피드백 속도는 테스트를 얼마나 빨리 실행하고, 실패 원인을 얼마나 쉽게 읽고, 팀과 같은 검증 결과를 재현할 수 있는지에 달려 있다.

## 1. IntelliJ IDEA와 명령줄에서 빠르게 실행하기

빌드 스크립트나 Gradle Toolchain에 지정된 JDK 버전을 확인하고, 명령줄과 IntelliJ IDEA에서 같은 빌드 설정을 사용한다.

| 확인할 범위 | 실행 방법 |
| --- | --- |
| 현재 테스트 메서드나 클래스 | 에디터의 거터 실행 아이콘으로 테스트나 클래스를 실행한다. 실패 지점을 확인할 때는 같은 위치에서 디버그한다. |
| 패키지나 변경 영향 범위 | Project 창의 패키지나 테스트 디렉터리에서 실행한다. 커밋 전에는 영향을 받는 테스트 모음도 확인한다. |
| 저장소 전체 | CI와 같은 Gradle Wrapper 명령을 사용한다. 프로젝트에서 별도 통합 테스트 태스크를 쓴다면 해당 태스크도 포함한다. |

Gradle 프로젝트에서 현재 클래스만 실행하고 전체 테스트로 범위를 넓히는 예는 다음과 같다.

```sh
./gradlew test --tests '*ResourceQueryTest'
./gradlew test
```

IDE의 Keymap에서 `Run Context Configuration`, `Rename`, `Extract Method`, `Change Signature`에 해당하는 동작을 확인한다. 변수나 상수 추출과 인라인도 테스트의 의도를 드러내는 데 쓸 수 있다. 여러 편집 동작에서 반복이 크면 에디터 매크로로 묶는다. 예를 들어 시나리오 문장을 테스트 이름 형식으로 바꾸는 작업을 줄일 수 있다. 사람이 읽는 문장을 실행 결과에 남기려면 JUnit의 `@DisplayName`도 사용할 수 있다.

Copilot은 반복되는 테스트 틀이나 경계값 후보를 제시하는 데 활용한다. 제안된 단언이 현재 구현의 출력을 그대로 베끼지 않았는지 요구사항과 대조하고, 실행해 예상한 결과가 나오는지 확인한다.

**공식 문서** [IntelliJ IDEA 테스트 실행](https://www.jetbrains.com/help/idea/performing-tests.html) · [리팩터링 동작](https://www.jetbrains.com/help/idea/refactoring-source-code.html) · [매크로](https://www.jetbrains.com/help/idea/using-macros-in-the-editor.html) · [Gradle 테스트 필터링](https://docs.gradle.org/current/userguide/java_testing.html#test_filtering) · [GitHub Copilot IDE 활용](https://docs.github.com/en/copilot/how-tos/copilot-in-your-ide/chat-with-copilot/chat-in-ide)

## 2. Spring 테스트 범위에 예산 배분하기

| 목적 | 실행 범위 |
| --- | --- |
| 입력 규칙과 반환값을 빠르게 반복 확인 | Spring 컨테이너 없이 호출하는 JUnit 테스트 |
| MVC 요청 매핑, 직렬화, 오류 응답 확인 | `@WebMvcTest`와 `MockMvc` 등 웹 계층 테스트. 사용 중인 보안 필터와 의존성 범위를 확인한다. |
| 실제 서버 시작, HTTP 왕복, 저장과 보안의 연동 확인 | `@SpringBootTest(webEnvironment = RANDOM_PORT)`에서 실행 서버에 접속하는 테스트 |
| 로컬에서 실제 요청의 모양을 탐색 | 실행한 서버에 HTTP 클라이언트로 요청해 헤더와 응답을 확인하고, 반복할 계약은 자동화한다. |

같은 설정을 반복해서 선언하면 테스트용 합성 애노테이션으로 묶을 수 있다. 테스트 클래스마다 프로필이나 빈 재정의가 달라지면 Spring 컨텍스트 캐시의 재사용률도 달라진다. 실행 시간은 컨텍스트 초기화, 외부 자원, 데이터 준비, 테스트 본문으로 나눠 측정한다. 테스트 대상이 아닌 고비용 작업에 가벼운 테스트 설정을 쓸 때는 그 작업 자체를 검증하는 범위와 운영 설정을 유지한다.

**공식 문서** [Spring Boot 테스트와 슬라이스](https://docs.spring.io/spring-boot/reference/testing/spring-boot-applications.html) · [MockMvc](https://docs.spring.io/spring-framework/reference/testing/mockmvc.html) · [Spring 컨텍스트 캐시](https://docs.spring.io/spring-framework/reference/testing/testcontext-framework/ctx-management/caching.html)

## 3. 테스트에서 시작하는 코드 리뷰와 CI

1. 변경한 테스트 이름을 훑어 어떤 요구사항이 추가되거나 달라졌는지 확인한다.
2. 사전 조건, 요청, 단언을 읽고 테스트가 계약을 지키는 경우와 위반한 경우를 구별할 수 있는지 본다.
3. CI에서 빌드와 테스트 결과를 확인하고 실패한 시나리오와 최초 원인을 읽는다.
4. 변경한 구현을 읽으며 구조, 책임, 오류 처리, 테스트가 관찰하기 어려운 영향까지 검토한다.

CI에서는 버전 관리된 Wrapper로 빌드와 테스트를 실행한다. 기본 브랜치에 Pull Request를 합치기 전 필요한 검사가 성공하도록 설정하고, 실패 보고서에 테스트 이름과 로그를 남긴다. 자주 실행하는 테스트가 느려지면 실행 수를 줄이기 전에 반복 준비 비용과 컨텍스트 재사용 여부를 측정한다.

**공식 문서** [GitHub Actions에서 Gradle 빌드와 테스트](https://docs.github.com/en/actions/tutorials/build-and-test-code/java-with-gradle) · [GitHub 필수 상태 검사](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging)
