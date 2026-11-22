# DB 우선 순차 쓰기에서 지급이 누락되는 경우

## 1. DB가 커밋된 뒤에 외부 호출을 시작한다

실패를 재현하는 기준 흐름은 `payout_request` 저장 → `COMMIT` → Ethereum RPC 제출이다. 첫 커밋은 접수 이력을 남기지만 두 번째 작업의 완료 여부는 외부에서 결정된다. [PostgreSQL 18 트랜잭션](https://www.postgresql.org/docs/18/tutorial-transactions.html) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Ethereum eth_sendRawTransaction](https://ethereum.org/developers/docs/apis/json-rpc/#eth-sendrawtransaction)

## 2. 일시적으로 남은 요청을 작업 유실과 구분한다

DB 커밋 직후 프로세스가 내려가면 요청 행만 남고 RPC 호출은 시작하지 않는다. 영속 작업 기록과 재개 절차가 없다면 `ACCEPTED` 상태가 계속 남는다. 요청과 Outbox를 함께 저장하면 DB에 남은 작업을 Relay가 이어갈 수 있다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

![DB가 먼저 반영되고 프로세스가 종료되어 외부 작업이 시작되지 않은 순차 쓰기 사례](image/01_dual_write.png)

그림의 근거 · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 3. 커밋 직후 중단하고 재기동 전후를 비교한다

로컬 체인 제출 직전 프로세스를 종료한다. 재기동한 뒤 요청 행, 미발행 Outbox 유무와 체인 거래 기록을 확인한다. 다음 실행에서는 요청과 작업 기록을 한 트랜잭션에 저장하고 재기동 후 처리 건수가 회복되는지 비교한다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Ethereum 개발 네트워크](https://ethereum.org/developers/docs/development-networks/)
