# RAG Fundamentals and Vector Store Retrieval

RAG는 답변을 생성할 때 애플리케이션 데이터에서 관련 근거를 검색해 모델에 제공한다. 최신 정책이나 내부 문서를 사용하는 경우, 어떤 문서의 어느 부분에서 답이 나왔는지 추적할 수 있게 설계한다. [Spring AI · Retrieval Augmented Generation](https://docs.spring.io/spring-ai/reference/2.0/api/retrieval-augmented-generation.html)

## 1. 적재와 질의

| 단계 | 처리 |
| --- | --- |
| 적재 | 문서를 읽고, 문단이나 토큰 단위로 나눈 뒤, 임베딩과 문서 ID·버전·청크 ID를 저장한다. |
| 질의 | 같은 임베딩 공간에서 질의를 벡터화하고, 권한·유효 버전 조건을 적용해 상위 청크를 찾는다. |
| 응답 | 검색된 구절을 바탕으로 답을 생성하고 근거 ID를 반환한다. 근거가 부족하면 그 상태를 명시한다. |

청크가 너무 크면 관련 사실이 묻히고 모델 입력이 늘어난다. 너무 작으면 조건과 예외가 다른 청크로 나뉠 수 있다. 제목·본문·예외 조건의 관계를 보존하면서 청크 크기와 겹침을 비교하고, 코사인 거리나 유사도 점수는 저장소가 정의한 방향과 범위를 확인한다. [Spring AI · ETL Pipeline](https://docs.spring.io/spring-ai/reference/2.0/api/etl-pipeline.html)

## 2. 작은 데이터로 검색부터 검증하기

반품, 교환, 배송의 짧은 가상 문서를 각각 적재한다. 반품 기간을 묻는 질의에서 반품 문서가 상위에 나오는지 먼저 확인한다. 이후 질의 표현을 바꾸거나 정책에 없는 항목을 묻고, 근거 ID와 답변 보류가 맞는지 확인한다.

`SimpleVectorStore`로 검색과 응답 흐름을 다듬고, 운영 데이터의 지속성이나 SQL 연계가 필요하면 `PgVectorStore`로 옮길 수 있다. 두 환경을 비교할 때 동일한 임베딩 모델과 테스트 문서를 사용한다. [Spring AI · Vector Databases](https://docs.spring.io/spring-ai/reference/2.0/api/vectordbs.html)

관련 문서 [Vector Databases and Similarity Search](06_vector_databases_and_similarity_search.md) · [Building Spring AI RAG with pgvector](20_building_spring_ai_rag_with_pgvector.md)
