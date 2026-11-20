# Serverless Microservices with Domain Boundaries

서버리스에서 HTTP, 큐, 스케줄이 실행을 시작하더라도 함수의 경계는 업무와 상태의 소유권을 기준으로 정한다. 하나의 도메인 서비스가 여러 함수로 배포될 수 있고, 같은 도메인 규칙을 여러 핸들러가 호출할 수 있다. [AWS Well-Architected · Serverless Applications Lens](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/welcome.html)

## 주문에서 입력 어댑터를 연결하는 사례

| 들어오는 신호 | 입력 어댑터와 유스케이스 |
| --- | --- |
| API Gateway에서 주문 생성 호출 | HTTP Lambda 핸들러가 요청을 명령으로 변환하고 주문 생성 포트를 호출한다. |
| 재고 예약 결과가 큐에 도착 | 큐 핸들러가 계약을 검증하고 주문 진행 유스케이스에 전달한다. |
| 오래 대기한 주문을 확인하는 스케줄 | 스케줄 핸들러가 재확인 유스케이스를 실행한다. |

함수 인스턴스의 메모리는 재사용될 수 있지만 주문의 상태를 복구할 근거는 소유 저장소에 둔다. 큐에는 중복 전달이 가능하므로 처리한 이벤트 키와 업무 상태의 저장 경계를 함께 고려한다. AWS Lambda의 SQS 이벤트 소스는 실패 시 배치를 다시 처리할 수 있고, 지원하는 부분 배치 응답을 사용하면 실패 항목만 다시 처리하게 할 수 있다. [AWS Lambda · Event Source Mapping](https://docs.aws.amazon.com/lambda/latest/dg/invocation-eventsourcemapping.html) · [AWS Lambda · SQS Error Handling](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html)

## 실행 방식의 선택 기준

호출이 간헐적이고 짧은 작업이라면 관리형 실행과 이벤트 연결을 활용할 수 있다. 지속 부하, 긴 작업, 엄격한 지연 요구가 있으면 컨테이너 구성과도 비교한다. 동시 실행 한도, 초기화 시간, DB 연결 수, 재시도와 실패 경로가 주문의 업무 계약에 어떤 영향을 미치는지 검토한다. 장시간 조율이 필요한 주문 Saga는 진행 상태를 외부에 보존하고 개별 단계의 책임을 명시한다.

주문 포트와 도메인 모델을 유지하면 실행을 시작하는 어댑터와 저장·메시징 어댑터를 구성에 맞춰 바꿀 수 있다. 권한, 전달 보장, 관측, 운영 책임은 새 배치에서 다시 확인한다. [Cockburn · Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture) · [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
