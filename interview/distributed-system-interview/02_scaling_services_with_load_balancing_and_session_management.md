# Scaling Services with Load Balancing and Session Management

## 8. 앱 서버를 여러 대로 늘렸다면 요청을 어떻게 분배하나요?

**30–60초 답변**

> 로드밸런서가 요청을 받고 준비된 앱 인스턴스로 보냅니다. 각 서버의 용량과 요청 처리 시간이 비슷하면 라운드 로빈부터 사용하겠습니다. 빠른 요청과 오래 걸리는 요청이 섞인다면 진행 중인 요청이 적은 서버를 우선하는 정책을 검토합니다. 대상별 진행 중 요청 수와 요청 유형별 p99를 비교해 어느 정책이 실제 대기 시간을 줄이는지 확인하겠습니다. [AWS ALB의 라우팅 알고리즘](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html)

**꼬리 질문 · 요청 수가 고른데도 느릴 수 있나요?**

같은 수의 요청을 받아도 일부 서버에 보고서 생성처럼 오래 걸리는 요청이 쌓일 수 있습니다. HTTP 요청 수와 연결 수도 서로 다른 지표입니다. NGINX의 `least_conn`은 활성 연결을 기준으로 하므로, 한 연결에서 여러 요청을 처리하는 환경에서는 같은 수의 연결이 같은 서버 부하를 뜻하는지 확인합니다. [NGINX HTTP 로드밸런싱](https://nginx.org/en/docs/http/load_balancing.html)

**꼬리 질문 · 자동 확장 기준은 어떻게 고르나요?**

CPU를 쓰는 처리 경로에는 인스턴스당 CPU가 유용합니다. I/O 대기가 병목이면 진행 중인 요청 수나 대기열을 후보로 삼고 p99와 오류율을 보며 검증합니다. 새 인스턴스가 준비되기까지 걸리는 시간과 DB 연결 예산도 반영합니다. [Azure Well-Architected Framework · Scaling](https://learn.microsoft.com/en-us/azure/well-architected/reliability/scaling)

## 9. 한 서버가 응답하지 않으면 이후 요청에서 어떻게 제외하나요?

**30–60초 답변**

> 로드밸런서가 각 인스턴스의 준비 상태를 주기적으로 확인하게 하겠습니다. 연속 실패 기준에 도달하면 신규 요청 대상에서 빼고, 복구 확인 뒤 다시 편입합니다. 실제 요청에서 연결 오류나 타임아웃이 반복될 때도 이상 대상으로 판단할 수 있습니다. 계획된 배포나 축소에서는 신규 요청을 먼저 막고 정해진 유예 시간 안에서 이미 받은 요청을 처리하도록 하겠습니다. [AWS ALB의 대상 상태 검사](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html) · [AWS ALB의 등록 해제 지연](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html#deregistration-delay) · [Envoy 이상 대상 제외](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)

**꼬리 질문 · 모든 서버가 사용하는 DB가 장애라면 모든 앱을 제외해야 하나요?**

대상 제외용 검사는 그 인스턴스를 우회하면 문제가 해결되는지 판단할 수 있게 설계합니다. 공용 DB의 상태만으로 모든 대상을 제외하면 DB를 쓰지 않는 경로도 영향을 받을 수 있습니다. 공용 의존성은 별도 지표와 경보로 관측하고, 영향을 받은 경로에는 대기 시간과 동시 요청 제한을 적용합니다. 정상 대상 수, 제외 사유, 재편입의 빈도를 함께 봅니다. [AWS Builders’ Library의 헬스 체크](https://aws.amazon.com/builders-library/implementing-health-checks/) · [Envoy 이상 대상 제외](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)

## 10. 다음 요청이 다른 서버로 갔다면 로그인 상태를 어떻게 유지하나요?

**30–60초 답변**

> A의 메모리에 세션이 있으면 B는 쿠키의 세션 ID만 받고 그 내용을 조회할 수 없습니다. 서버 세션을 유지한다면 Redis 같은 공유 저장소에 세션을 두고, 모든 앱이 같은 ID로 조회하게 하겠습니다. TTL로 만료를 관리하고 로그아웃할 때 세션을 삭제합니다. 매 요청의 저장소 조회를 줄이는 편이 더 중요하고 권한 변경은 토큰 만료까지 기다릴 수 있다면 짧은 수명의 서명 토큰을 검토합니다. [Spring Session과 Redis](https://docs.spring.io/spring-session/reference/guides/boot-redis.html) · [JWT 보안 권고 RFC 8725](https://www.rfc-editor.org/rfc/rfc8725)

**꼬리 질문 · 공유 저장소가 느려지거나 토큰을 즉시 폐기해야 한다면요?**

공유 세션 방식에서는 저장소 조회 p99, 연결 오류, 실제로 세션이 없는 응답을 따로 집계합니다. 인증 상태를 확인할 수 없으면 보호된 요청을 제한합니다. 서명 토큰을 즉시 폐기하려면 폐기 목록이나 발급자 상태처럼 요청 때 확인할 경로가 필요합니다. 비대칭 서명에서는 발급자가 개인 키를 보유하고, 앱이 공개 키로 서명과 만료·발급자·대상을 검증합니다. 키를 교체할 때는 새 키를 먼저 배포하고 기존 토큰의 만료까지 이전 키도 검증에 사용합니다. [Spring Session API](https://docs.spring.io/spring-session/reference/api.html) · [JWT 보안 권고 RFC 8725](https://www.rfc-editor.org/rfc/rfc8725) · [토큰 폐기 RFC 7009](https://www.rfc-editor.org/rfc/rfc7009)

## 11. 같은 사용자를 계속 같은 서버에 보내면 증설과 장애 때 어떤 문제가 생기나요?

**30–60초 답변**

> 세션 고정은 같은 사용자를 기존 서버에 보내 로컬 세션을 이어가는 방법입니다. 증설 직후에는 기존 연결이나 쿠키가 이전 서버를 계속 가리켜 새 서버로 부하가 즉시 옮겨가지 않을 수 있습니다. 특정 사용자의 요청이 한 서버에 집중될 수도 있습니다. 기존 서버가 장애로 빠지면 대체 서버로 요청은 보낼 수 있어도 이전 메모리 세션을 읽을 수 없어 다시 로그인할 수 있습니다. [AWS ALB 세션 고정](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html#sticky-sessions)

**꼬리 질문 · 개선 효과를 어떻게 확인하나요?**

같은 요청량으로 대상별 요청 수, 처리 중 요청 수와 p99를 비교하고, 인스턴스를 교체한 뒤 세션 조회 실패율과 인증 리다이렉트 비율을 확인합니다. 앱을 어디로 보내도 동일하게 인증할 수 있는 구조를 선택했다면 대상 하나를 제외해도 이미 로그인한 사용자가 계속 요청을 처리할 수 있는지 시험합니다.

## 12. 앱을 늘린 뒤 DB가 병목처럼 보이면 무엇부터 확인하나요?

**30–60초 답변**

> 요청 추적에서 앱의 DB 연결 획득 대기와 연결을 받은 뒤 SQL이 실행되는 시간을 따로 봅니다. 연결 대기만 늘었다면 풀의 사용 중 연결 수와 대기 요청, 트랜잭션이 연결을 잡는 시간을 확인합니다. SQL도 느려졌다면 DB CPU·I/O·잠금 대기와 상위 쿼리의 실행 계획을 같이 봅니다. 앱 네 대가 같은 DB에 각각 최대 20개를 연결하면 앱만 최대 80개입니다. 자동 확장 최대치, 배포 중 신구 인스턴스의 중복, 배치·운영 연결까지 합해 DB가 목표 지연을 지킬 수 있는 연결 예산을 정하겠습니다. [HikariCP 최대 풀 크기](https://github.com/brettwooldridge/HikariCP#configuration-knobs-baby) · [PostgreSQL 실행 계획](https://www.postgresql.org/docs/current/using-explain.html)

**꼬리 질문 · 풀 대기만 높을 때 풀을 키우면 되나요?**

DB 자원과 연결 예산에 여유가 있고 정상적인 동시 처리량이 현재 풀 크기를 넘는지 확인한 뒤 조정합니다. 풀을 키우기 전에 열린 채 오래 머무는 트랜잭션과 연결 누수를 확인합니다. DB가 이미 포화됐다면 동시 실행을 제한하고 느린 쿼리나 잠금을 먼저 개선합니다. `인스턴스별 풀 최대치의 합계 + 다른 클라이언트의 연결 예산`을 대상 DB마다 계산하고, 부하 테스트에서 획득 대기·SQL 지연·성공 RPS를 함께 비교합니다. [HikariCP 풀 크기 산정](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing)

## 13. DB 요청의 90%가 읽기라면 어떻게 개선하나요?

**30–60초 답변**

> 읽기 비율과 함께 쿼리별 호출 횟수와 누적 실행 시간을 보겠습니다. 자원을 많이 쓰는 조회는 실행 계획을 보고 조건과 정렬에 맞는 인덱스나 쿼리 개선을 먼저 검증합니다. 같은 키를 반복해서 읽고 잠시 오래된 값이 허용되는 상품 조회에는 캐시를 적용해 적중률과 실제 DB 읽기 수를 측정하겠습니다. 캐시로 효과를 보기 어려운 읽기가 계속 주 DB를 포화시키면 허용 가능한 조회를 읽기 복제본으로 보냅니다. 주문 생성 직후 본인의 주문은 커밋이 끝난 주 DB에서 조회해 방금 쓴 내용을 보여주겠습니다. [PostgreSQL 실행 계획](https://www.postgresql.org/docs/current/using-explain.html) · [Redis cache-aside](https://redis.io/docs/latest/develop/use-cases/cache-aside/) · [PostgreSQL 스트리밍 복제](https://www.postgresql.org/docs/current/warm-standby.html#STREAMING-REPLICATION)

**꼬리 질문 · 쓰기 직후 읽기도 복제본으로 보내려면요?**

쓰기 커밋의 로그 위치를 이후 읽기에 전달할 수 있다면 해당 위치까지 적용된 복제본을 선택합니다. 요청의 기한 안에 조건을 충족하는 복제본이 없으면 주 DB로 보냅니다. 읽기 경로에 캐시가 있다면 최신 값이 필요한 요청은 캐시도 우회하거나 버전을 검사합니다. 오래된 값이 허용되는 경로는 복제 지연 상한과 초과 시의 라우팅 정책을 정하고, 쓰기 직후 읽기 테스트와 주 DB로 돌아오는 요청 비율을 확인합니다. [PostgreSQL Read-Your-Writes Consistency](https://www.postgresql.org/docs/current/warm-standby.html)

**꼬리 질문 · 인덱스와 캐시를 추가하면 무엇을 비교하나요?**

인덱스를 반영한 뒤 조회 지연과 읽은 페이지 수가 줄었는지 보고, 쓰기 지연과 인덱스 공간 증가도 확인합니다. 캐시는 상품 정보가 바뀔 때 커밋 후 키를 무효화하고, 허용하는 데이터 노후 시간에 맞춰 TTL을 정합니다. 캐시 미스나 장애가 몰릴 때 DB 읽기와 지연이 감당 가능한지도 부하 테스트로 확인합니다. [PostgreSQL 실행 계획](https://www.postgresql.org/docs/current/using-explain.html) · [Redis cache-aside](https://redis.io/docs/latest/develop/use-cases/cache-aside/)
