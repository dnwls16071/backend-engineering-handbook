# Retrying Transient Failures in TCC

TCC 재시도는 전송 실패와 업무 거절을 구별한다. 커밋 뒤 응답이 유실될 수 있으므로 재요청에는 같은 분기 키와 내용을 쓴다. [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/)

## 1. 원인과 현재 결정에 맞춰 재시도한다

| 경우 | 처리 | 근거 |
| --- | --- | --- |
| 네트워크 단절·타임아웃 | 결과 미상으로 저장하고 제한된 재시도 또는 상태 조회로 판별한다. | [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) |
| 재고 부족 또는 동일 키의 다른 요청 | 업무 결과나 충돌로 남겨 자동 반복을 피한다. | [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) |
| 확정 결정 뒤 일시 실패 | 재개 시 같은 참가 분기의 Confirm을 반복한다. | [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) · [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) |

## 2. 재시도의 부하와 지연을 제한한다

호출 한도, 전체 마감, 지터가 있는 백오프를 정한다. 동기 응답 시간이 끝나면 복구 큐에 넘기고 현재 결정과 참가 결과를 유지한다. 여러 호출 계층이 같은 재시도를 중첩하지 않게 한다. [AWS · Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) · [AWS · Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)
