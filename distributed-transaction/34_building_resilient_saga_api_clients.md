# Building Resilient Saga API Clients

조정자의 HTTP 클라이언트는 참가자 응답을 업무 성공·거절·결과 미상으로 분류한다. 전송 재시도에 같은 operationId를 사용한다. [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)

## 1. 오류 분류를 호출 계약에 명시한다

참가자 계약에서 확정한 재고 부족은 업무 거절이다. 요청 타임아웃과 연결 중단은 결과 미상이다. 5xx도 서버가 커밋한 뒤 발생할 수 있어 해당 API가 명시한 의미와 멱등 정책을 기준으로 분류한다. [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted)

## 2. 재시도 시간과 관측 키를 정한다

시도마다 제한 시간과 전체 마감을 잡고 일시 오류에만 지터 백오프를 적용한다. 조정 기록에 sagaId, 단계, operationId, 시도 번호를 남기되 요청의 불필요한 민감 정보는 저장하지 않는다. [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)
