# Designing a URL Shortener

URL 단축기는 짧은 코드로 원래 URL을 찾는다. 생성과 리다이렉트의 처리량이 다르고, 링크를 변경하거나 만료시킬 수 있는지가 캐시 정책을 좌우한다. [RFC 9110 HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) · [RFC 9111 HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html) · [Microsoft Cache-Aside](https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside)

## 1. 쓰기 경로에서 단축 코드를 확정한다

POST로 http 또는 https URL을 받고 코드, 원래 URL, 소유자와 만료 시각을 저장한다. 무작위 Base62 코드라면 DB의 코드를 고유하게 만들고 충돌할 때 새 코드를 생성한다. 같은 생성 요청을 다시 받으면 업무 멱등 키로 기존 코드를 돌려준다. [PostgreSQL 18 Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html) · [AWS Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 2. 읽기 경로에서 상태와 캐시를 확인한다

GET으로 코드의 목적지를 조회한 뒤 302와 Location을 반환한다. 영구 이동인 301은 영구 링크 정책일 때 검토한다. 변경·폐기 가능한 링크에는 명시적인 캐시 정책을 적용하고, 링크 무효화 이후 기존 캐시의 잔존 시간을 관리한다. [RFC 9110 HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) · [RFC 9111 HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html) · [Microsoft Cache-Aside](https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside)

## 3. 인기 링크와 만료를 시험한다

한 링크에 리다이렉트가 집중될 때 원본 DB 조회 수와 엣지 적중률을 확인한다. 사용자 행동 집계는 리다이렉트 응답 밖에서 처리하고, 삭제되거나 만료된 코드를 캐시가 계속 전달하는지 재현한다. [Microsoft Cache-Aside](https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside) · [Microsoft Queue-Based Load Leveling](https://learn.microsoft.com/en-us/azure/architecture/patterns/queue-based-load-leveling) · [Google SRE · Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
