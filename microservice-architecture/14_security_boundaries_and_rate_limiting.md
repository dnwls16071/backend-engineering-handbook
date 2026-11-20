# Security Boundaries and Rate Limiting

보안 경계에서 인증은 요청의 주체를 확인하고, 인가는 그 주체가 기능이나 주문을 사용할 수 있는지 판단한다. 게이트웨이가 토큰의 진위와 범위를 검사하더라도 주문 서비스는 자신의 데이터와 업무 규칙에 따라 접근 권한을 판단한다. [OWASP API Security Top 10](https://api-security.owasp.org/editions/2023/en/0x11-t10/) · [OAuth 2.0 JWT Access Token Profile](https://www.rfc-editor.org/rfc/rfc9068.html)

## 게이트웨이와 도메인에서 지킬 규칙

- 외부 어댑터는 인증된 사용자·테넌트 정보를 검증하고, 신뢰할 수 있는 주체 정보를 애플리케이션에 전달한다.
- 주문 조회는 주체가 해당 주문을 볼 수 있는지 확인한다. 관리자 기능과 노출할 응답 필드도 각자 정책을 둔다.
- 메시지·배치의 주체와 권한을 정한다. 웹이 아닌 입력 포트에서도 보호해야 하는 업무 인가가 유지되는지 확인한다.

| OWASP 위험 범위 | 주문 시스템에서 검토할 지점 |
| --- | --- |
| 객체·속성·기능 수준 인가, 인증 실패 | 주문의 소유권, 필드 접근, 운영자 기능과 사용자 기능, 토큰 검증 |
| 자원 소모와 민감한 업무 흐름 남용 | 요청 한도, 조회 비용, 구매·예약 횟수의 업무 규칙 |
| SSRF, 설정, API 목록 관리, 외부 API의 안전한 소비 | 허용된 외부 연결, 공개 경로의 목록, 설정 점검, 외부 응답 검증 |

## 분산 환경에서 요청 한도 정하기

고정 윈도는 단순하지만 경계 직전·직후에 요청이 몰릴 수 있다. 슬라이딩 윈도는 최근 구간을 기준으로 세고, Token Bucket은 일정한 보충률과 짧은 버스트 허용량을 표현한다. Spring Cloud Gateway의 Redis 기반 RequestRateLimiter는 Token Bucket을 지원한다. [Spring Cloud Gateway · RequestRateLimiter](https://docs.spring.io/spring-cloud-gateway/reference/spring-cloud-gateway-server-webflux/gatewayfilter-factories/requestratelimiter-factory.html)

예를 들어 초당 10토큰 보충, 최대 20토큰, 요청당 1토큰이라면 빈 트래픽 이후의 짧은 버스트와 지속 허용량이 다르다. 한도 키는 검증된 사용자의 식별자와 경로별 정책으로 정한다. 인스턴스 여러 개에서 공유해야 하는 한도와 각 인스턴스의 자원 보호를 구분하고, 제한 저장소 장애 때 고비용 경로와 조회 경로의 처리 방식을 각각 정한다. 한도를 넘긴 응답에는 `429`를 사용하고 재요청 가능 시점을 알려줄 수 있다. [RFC 6585 · 429](https://www.rfc-editor.org/rfc/rfc6585.html#section-4) · [Redis 슬라이딩 윈도 설계](../redis/07_sliding_window_api_rate_limiting_with_redis_sorted_sets.md)
