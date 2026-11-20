# Spring AI Fundamentals and LangChain Comparison

Spring AI는 Spring 애플리케이션에서 모델, 임베딩, 벡터 저장소를 연결할 공통 인터페이스와 Spring Boot 자동 설정을 제공한다. 서비스의 비즈니스 로직은 모델 응답을 검증하고 사용자에게 제공할 형태를 정한다. [Spring AI · 프로젝트 개요](https://spring.io/projects/spring-ai)

## 1. Spring AI 1.0 GA와 실습 버전

Spring AI 1.0은 2025년 5월 GA로 공개됐다. 첫 정식 릴리스는 모델 호출, 벡터 검색, 도구 연결을 Spring 애플리케이션에 통합하는 기반을 제공했다. 이 문서 모음의 실습은 Spring Boot 4.1.0과 Spring AI 2.0.2를 사용한다. Spring AI 2.0 계열의 공식 호환 범위에는 Spring Boot 4.0과 4.1이 포함된다. 먼저 BOM과 선택한 모델 스타터의 버전을 맞춘다. [Spring AI 1.0 GA 발표](https://spring.io/blog/2025/05/20/spring-ai-1-0-GA-released/) · [Spring AI 2.0 GA 발표](https://spring.io/blog/2026/06/12/spring-ai-2-0-0-GA-available-now/) · [Spring AI · 의존성 관리](https://docs.spring.io/spring-ai/reference/2.0/getting-started.html)

## 2. Spring AI와 LangChain의 선택 기준

| 기준 | Spring AI | LangChain Python |
| --- | --- | --- |
| 실행 환경 | Java와 Spring Boot의 빈, 프로파일, 웹 계층에 통합한다. | Python에서 모델과 도구, 검색 구성 요소를 조합한다. |
| 모델 호출 | `ChatModel`로 공통 모델 계약을 사용하고 `ChatClient`로 요청을 구성할 수 있다. | 채팅 모델을 초기화하고 `invoke()`나 `stream()`으로 호출한다. |
| 벡터 검색 | `VectorStore`와 `SearchRequest`로 저장과 검색을 구성한다. | 저장소 통합을 선택하고 `similarity_search()`나 retriever를 이용한다. |

기존 Spring 서비스 안에서 인증과 REST 계약을 함께 운영한다면 Spring AI가 자연스럽다. Python 서비스에서 이미 LangChain 통합을 쓰고 있다면 같은 경계에서 모델과 검색 흐름을 운영할 수 있다. 팀의 배포·테스트 환경과 필요한 모델 기능을 기준으로 고른다. [LangChain · Models](https://docs.langchain.com/oss/python/langchain/models) · [LangChain · Vector stores](https://docs.langchain.com/oss/python/integrations/vectorstores) · [Spring AI · Chat Client](https://docs.spring.io/spring-ai/reference/2.0/api/chatclient.html)

## 3. ChatModel과 VectorStore의 경계

- `ChatModel`은 메시지를 담은 `Prompt`를 받아 모델을 호출한다. 텍스트 외에 생성 결과와 메타데이터를 처리해야 하면 `ChatResponse`를 확인한다. 모델을 바꿀 때는 도구 호출, 스트리밍, 옵션의 동작을 같은 입력으로 확인한다. [Spring AI · Chat Model](https://docs.spring.io/spring-ai/reference/2.0/api/chatmodel.html)
- `VectorStore`는 문서와 메타데이터를 저장하고, 질의와 유사한 문서를 반환한다. 같은 인터페이스라도 인덱스 설정, 거리 함수, 점수 해석, 필터 지원은 저장소 설정에 따라 달라질 수 있다. [Spring AI · Vector Store](https://docs.spring.io/spring-ai/reference/2.0/api/vectordbs.html)

배송 FAQ를 답하는 서비스는 먼저 벡터 저장소에서 관련 정책을 읽고, 그 내용을 채팅 모델에 전달한다. 검색 결과가 비었을 때 안내할 응답까지 서비스에서 정한다.
