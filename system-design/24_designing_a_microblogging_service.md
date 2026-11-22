# Designing a Microblogging Service

단문 게시물의 원본, 팔로우 관계, 홈 타임라인, 검색 인덱스는 갱신 빈도와 최신성 요구가 다를 수 있다. 게시 직후 내 글을 보는 경로와 다른 이용자의 홈 목록을 별도로 설계한다. [Microsoft Cache-Aside](https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Google SRE · Implementing SLOs](https://sre.google/workbook/implementing-slos/)

## 1. 쓰기와 파생 갱신 경로를 연결한다

게시글을 저장하면서 TweetCreated에 해당하는 내부 이벤트를 Outbox에 남긴다. 게시자 프로필은 원본이나 최신성 보장 경로에서 읽고, 홈 목록과 검색 인덱스는 별도 소비자가 채울 수 있다. 이벤트에는 게시글·작성자 ID와 버전을 넣는다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Kafka 4.3 Introduction](https://kafka.apache.org/43/getting-started/introduction/) · [Microsoft Cache-Aside](https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside)

## 2. 인기 작성자의 쓰기 증폭을 줄인다

일반 작성자의 글은 팬아웃 작업이 팔로워별 홈 목록에 추가하고, 팔로워 규모가 큰 작성자의 최근 글은 사용자 홈을 읽을 때 병합하는 방식이 가능하다. 홈의 정렬 키에 고유 ID를 포함해 페이지를 이어 읽는다. [Microsoft Queue-Based Load Leveling](https://learn.microsoft.com/en-us/azure/architecture/patterns/queue-based-load-leveling) · [Google SRE · Handling Overload](https://sre.google/sre-book/handling-overload/) · [PostgreSQL 18 Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)

## 3. 삭제·차단 이후의 화면을 검증한다

삭제와 공개 범위 변경은 원본에서 먼저 확인한다. 오래된 홈 인덱스에 ID가 남아도 현재 권한으로 가려야 하며, 이벤트 재전달이 과거 게시물을 목록에 되살리지 않도록 버전을 확인한다. 발행부터 홈 반영까지의 지연을 추적한다. [Microsoft Cache-Aside](https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Google SRE · Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
