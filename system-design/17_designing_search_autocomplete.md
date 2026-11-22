# Designing Search Autocomplete

자동완성은 입력 중인 접두사로 소수의 추천 질의를 반환한다. 문서 전문 검색과 다른 응답 한도, 추천 기준과 갱신 주기를 정한다. [Elasticsearch Completion](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/completion) · [Google SRE · Implementing SLOs](https://sre.google/workbook/implementing-slos/)

## 1. 후보를 만들고 순위를 매긴다

정규화한 용어와 집계 점수로 접두사 인덱스를 만든다. 구현 예로 trie의 접두사 노드에 상위 후보를 보관하거나, Elasticsearch completion 필드에 input과 weight를 저장할 수 있다. 동점의 결과 순서와 언어별 정책은 명시한다. [Elasticsearch Completion](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/completion)

## 2. 추천 조회와 집계 갱신을 분리한다

입력마다 전체 로그를 스캔하는 대신 최근 집계한 후보를 읽는다. 인기 접두사는 작은 결과를 캐싱하고, 언어·지역·정책이 달라질 때 같은 캐시 키를 공유하지 않도록 한다. 개인 식별 정보가 든 질의는 추천 후보에 포함되지 않게 필터링한다. [Elasticsearch Completion](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/completion) · [Microsoft Cache-Aside](https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside)

## 3. 품질과 지연을 따로 측정한다

접두사 길이와 언어별 p95 지연, 추천 전환율 및 새 용어가 반영되기까지의 시간을 기록한다. 인기 점수가 급변하거나 인덱스 배포가 실패할 때 이전 인덱스로 읽기를 이어갈 수 있는지 검증한다. [Elasticsearch Completion](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/completion) · [Google SRE · Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) · [Google SRE · Implementing SLOs](https://sre.google/workbook/implementing-slos/)
