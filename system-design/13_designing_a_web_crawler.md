# Designing a Web Crawler

웹 크롤러는 URL 발견, 가져오기, 문서 저장을 분리한다. URL 큐가 커져도 대상 호스트를 과부하시키지 않도록 수집 정책과 일정을 따로 관리한다. [RFC 9309 Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309.html) · [Microsoft Queue-Based Load Leveling](https://learn.microsoft.com/en-us/azure/architecture/patterns/queue-based-load-leveling)

## 1. URL을 발견하고 호스트별 작업으로 나눈다

시드 URL에서 발견한 링크를 절대 URL로 바꾸고 정규화한다. 스킴·호스트 같은 표준화 가능한 부분을 먼저 정리하고, 의미가 다른 쿼리 파라미터는 유지한다. 후보 URL과 컨텐츠 해시의 중복 처리는 각각 기록한다. [RFC 9110 HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) · [PostgreSQL 18 Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)

## 2. 수집 정책과 호스트별 한도를 적용한다

요청하기 전에 해당 호스트의 robots.txt를 읽고 크롤러의 User-agent에 적용되는 규칙을 평가한다. 호스트별 동시성, 요청 간격과 재시도 상한을 두고 오류가 지속되면 지연한다. 수집 대상은 허용된 공개 HTTP 경로로 제한한다. [RFC 9309 Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309.html) · [AWS Backoff and Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)

## 3. 가져오기와 저장의 실패를 복구한다

HTTP 상태·리다이렉트와 콘텐츠 유형을 검사한 뒤 본문, 최종 URL과 수집 시각을 저장한다. 재시작 시 작업 큐에서 같은 URL을 다시 가져올 수 있으므로 저장을 중복에 안전하게 만들고, 도메인별 실패와 대기 작업의 최고 체류 시간을 측정한다. [RFC 9110 HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) · [AWS Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Google SRE · Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
