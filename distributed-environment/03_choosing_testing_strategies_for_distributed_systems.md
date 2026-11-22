# Choosing Testing Strategies for Distributed Systems

같은 주문 기능도 업무 규칙이 틀린 경우, 저장소 연결이 틀린 경우, 서비스 응답 규격이 바뀐 경우를 따로 재현할 수 있다. 가장 좁은 경계에서 오류를 찾아낼 수 있는 테스트를 고른다. [Ham Vocke · The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)

## 1. 실패 유형과 테스트 경계를 연결한다

| 테스트 | 주문·재고 예시 | 남는 확인 사항 | 근거 |
| --- | --- | --- | --- |
| 단위 | 재고가 부족하면 주문 계산 로직이 예약 요청을 만들지 않는다. | 실제 HTTP 요청 형식, DB 제약 | [Ham Vocke · The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) |
| 통합 | 실제 DB에서 예약 저장 시 유니크 제약과 트랜잭션 롤백을 확인한다. | 배포된 서비스 사이의 전체 요청 경로 | [Ham Vocke · The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) · [Testcontainers for Node.js · PostgreSQL](https://node.testcontainers.org/modules/postgresql/) |
| 계약 | 주문 클라이언트가 요구한 수량 필드와 상태 코드를 재고 서비스가 제공한다. | 프로덕션의 네트워크 설정, 처리 지연, 전체 주문 완료 | [Pact JS · Consumer Tests](https://docs.pact.io/implementation_guides/javascript/docs/consumer) · [Pact JS · Provider Verification](https://docs.pact.io/implementation_guides/javascript/docs/provider) |
| 종단 간 | 외부 주문 API로 요청해 재고 예약과 주문 상태가 완료될 때까지 확인한다. | 모든 분기와 극단 입력은 별도의 좁은 테스트로 확인 | [Ham Vocke · The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) |

## 2. 실패 시나리오는 관찰 가능한 결과로 표현한다

타임아웃은 1회 실패 뒤 정상 응답과 지속 실패를 각각 검사한다. 중복 메시지는 같은 키로 재전달한 뒤 저장된 예약 건수와 최종 상태를 확인한다. 여러 서비스가 필요한 시나리오에는 완료 조건과 최대 대기 시간을 정한다. [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) · [AWS Lambda · Using Lambda with SQS](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html) · [Ham Vocke · The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)

## 3. 실습으로 이어가기

테스트 경계를 [Jest 단위 테스트](04_writing_unit_tests_with_jest.md), [통합·종단 간 테스트](05_exercising_integration_and_end_to_end_tests.md), [Pact 계약 테스트](06_verifying_service_contracts_with_pact.md) 순서로 비교한다. [Ham Vocke · The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) · [Pact JS · Consumer Tests](https://docs.pact.io/implementation_guides/javascript/docs/consumer)
