# Prompt Templates, Evaluation, and Injection Defenses

프롬프트는 서비스 계약의 일부다. 역할, 입력, 제약, 출력 형식, 톤을 명시하고 같은 데이터로 버전별 품질을 비교한다. [Spring AI · Prompts](https://docs.spring.io/spring-ai/reference/2.0/api/prompt.html)

## 1. 템플릿과 메시지 역할

시스템 메시지에는 업무 규칙과 출력 계약을, 사용자 메시지에는 요청과 데이터를 둔다. 이전 응답이 필요하면 어시스턴트 메시지로 구성한다. `PromptTemplate`에 쓰는 문구는 예를 들어 `src/main/resources/prompts/review.st`에 보관하고, 리뷰 본문 같은 값은 런타임 변수에 바인딩한다. 템플릿 버전은 평가 결과와 함께 남긴다. [Spring AI · Prompts](https://docs.spring.io/spring-ai/reference/2.0/api/prompt.html)

| 기법 | 적용 |
| --- | --- |
| Zero-shot | 규칙과 출력 형식만으로 초기 기준을 만든다. |
| Few-shot | 중립 리뷰나 의견이 섞인 리뷰처럼 경계가 모호한 사례를 예제로 준다. |
| Chain-of-thought 계열 | 여러 단계가 필요한 업무는 검증 가능한 중간 산출물, 근거 인용과 짧은 결론을 요청한다. |

한국어 품질은 존댓말, 도메인 용어, 날짜·단위, 부정문, 다국어가 섞인 요청을 별도로 평가한다. A/B 비교 시 모델 ID, 도구 권한, 테스트 입력과 채점 기준을 고정한다. 최소 지표는 JSON 파싱 성공률, 요구 필드 충족률, 근거와 표현의 일치율이다.

## 2. 프롬프트 인젝션 방어

사용자 입력, 검색 문서와 도구 결과를 모두 외부 데이터로 취급한다. 메시지 역할 나누기와 데이터 구역 표시를 적용하고, 문서 접근 권한은 서버에서 필터링한다. 도구는 허용된 이름·인자·범위로 제한하고, 상태 변경은 애플리케이션에서 권한을 다시 확인한다. 출력 스키마를 검증한 다음 업무 로직에 전달한다. [OWASP · LLM Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)

합성 문서에 지시문처럼 보이는 문장을 넣어도 앱의 도구 권한과 검색 범위가 유지되는지 회귀 테스트한다. 차단·승인 판단과 로그에는 원문을 줄이고 정책 ID와 결과를 기록한다.

관련 문서 [Operating AI Services with Observability and Guardrails](26_operating_ai_services_with_observability_and_guardrails.md)
