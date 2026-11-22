# 독립적으로 커밋되는 시스템과 지급 불변식

## 1. 두 시스템에서 확인할 사실을 구분한다

PostgreSQL은 하나의 트랜잭션 변경을 함께 커밋한다. Ethereum에서는 RPC가 제출 해시를 반환할 수 있고, 거래가 블록에 포함된 뒤 해시로 영수증을 조회할 수 있다. 이 시점들은 서로 독립적이다. [PostgreSQL 18 트랜잭션](https://www.postgresql.org/docs/18/tutorial-transactions.html) · [Ethereum eth_sendRawTransaction](https://ethereum.org/developers/docs/apis/json-rpc/#eth-sendrawtransaction) · [Ethereum eth_getTransactionReceipt](https://ethereum.org/developers/docs/apis/json-rpc/#eth-gettransactionreceipt)

## 2. 업무별로 지켜야 할 조건을 쓴다

StablePay의 불변식은 같은 `payout_id`로 최종 성공한 업무상 송금 효과가 최대 하나이고, `COMPLETED`는 대상 체인·수신자·금액에 맞는 성공이 확정된 뒤에만 기록되는 것이다. 내부 요청의 식별자를 보존하고, 여러 번 조회되거나 알림이 반복돼도 같은 업무 건으로 묶는다. [AWS 멱등 재시도](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Ethereum eth_getTransactionReceipt](https://ethereum.org/developers/docs/apis/json-rpc/#eth-gettransactionreceipt) · [Ethereum PoS 확정성](https://ethereum.org/developers/docs/consensus-mechanisms/pos/#finality)

![데이터베이스 기록과 외부 지급 효과를 독립적으로 확인해야 하는 두 쓰기 경계](image/01_dual_write.png)

그림의 근거 · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 3. 최대 한 번과 유실 방지를 각각 시험한다

같은 요청을 동시에 두 번 보냈을 때 같은 `payout_id`에 성공 송금이 하나인지 확인한다. 접수 직후 프로세스를 재시작한 경우에도 지급 작업을 DB에서 찾을 수 있어야 한다. 결과가 불명확한 요청은 계속 추적할 수 있게 보존하고 기한이 지나면 `REVIEW_REQUIRED`로 올린다. [AWS 멱등 재시도](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [AWS 타임아웃과 재시도](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
