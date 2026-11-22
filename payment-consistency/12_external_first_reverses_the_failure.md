# 외부 우선 순차 쓰기에서 추적할 요청이 사라지는 경우

## 1. 외부 제출 뒤에 내부 기록을 만든다

순서를 Ethereum RPC 제출 → 지급 요청 저장으로 바꾸면, 제출이 처리된 뒤 DB 저장에 실패할 수 있다. 외부에 효과가 남았는지는 DB가 복구된 뒤에도 체인에서 확인해야 한다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Ethereum eth_sendRawTransaction](https://ethereum.org/developers/docs/apis/json-rpc/#eth-sendrawtransaction) · [Ethereum eth_getTransactionReceipt](https://ethereum.org/developers/docs/apis/json-rpc/#eth-gettransactionreceipt)

## 2. 미확인 송금을 새 지급으로 이어가지 않는다

제출을 처리한 RPC 응답까지 사라지면 내부에는 요청도 해시도 없을 수 있다. 호출자의 재시도가 곧바로 새로운 송금을 만들면 기존 거래까지 함께 포함될 위험이 있다. 외부 호출 전에 요청과 시도의 식별자를 영속화하면 같은 건으로 조회할 근거가 남는다. [AWS 타임아웃과 재시도](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) · [AWS 멱등 재시도](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Ethereum eth_getTransactionReceipt](https://ethereum.org/developers/docs/apis/json-rpc/#eth-gettransactionreceipt)

![외부 쓰기 뒤 내부 기록이 실패하면 바깥에만 지급 효과가 남을 수 있는 순서](image/01_dual_write.png)

그림의 근거 · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 3. 누락된 내부 행과 남아 있는 외부 기록을 대조한다

로컬 체인에서 거래가 포함됐음을 확인한 뒤 내부 DB 쓰기를 실패시킨다. PostgreSQL에서 지급 행이 없는지, 외부에서는 해시의 영수증을 볼 수 있는지 확인한다. 테스트 도구에만 남겨 둔 해시 없이 애플리케이션이 이 거래를 찾을 수 있는지도 점검한다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [PostgreSQL 18 트랜잭션](https://www.postgresql.org/docs/18/tutorial-transactions.html) · [Ethereum eth_getTransactionReceipt](https://ethereum.org/developers/docs/apis/json-rpc/#eth-gettransactionreceipt) · [Ethereum 개발 네트워크](https://ethereum.org/developers/docs/development-networks/)
