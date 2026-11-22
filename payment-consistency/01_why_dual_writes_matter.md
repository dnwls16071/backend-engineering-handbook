# 결제 백엔드에서 Dual Write가 문제가 되는 이유

## 1. 지급 접수와 송금을 각각 기록한다

Dual Write는 한 업무가 서로 다른 두 시스템에 쓰기를 수행하는 경우다. 예를 들어 지급 API가 PostgreSQL에 지급 요청을 저장하고, 별도의 Ethereum RPC를 호출해 송금 트랜잭션을 제출하면 각 쓰기가 자체 경계에서 처리된다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Ethereum eth_sendRawTransaction](https://ethereum.org/developers/docs/apis/json-rpc/#eth-sendrawtransaction)

## 2. 한쪽만 반영되는 순간을 찾는다

요청을 먼저 커밋한 뒤 프로세스가 종료되면 지급 요청만 남는다. 반대로 송금을 먼저 제출한 뒤 내부 쓰기에 실패하면 외부에서 거래가 진행되지만 요청을 추적할 행이 없을 수 있다. 불일치는 각 시스템의 변경이 확정되는 시점 사이에서 생긴다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Ethereum eth_sendRawTransaction](https://ethereum.org/developers/docs/apis/json-rpc/#eth-sendrawtransaction)

![두 쓰기 사이의 장애가 실행 순서에 따라 서로 다른 불일치를 남기는 예시](image/01_dual_write.png)

그림의 근거 · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 3. 두 시스템에서 확인할 결과를 정한다

실습에서는 로컬 체인과 테스트 계정으로 두 실행을 격리하고, 같은 조건의 지급을 양쪽 순서에서 한 번씩 실행한다. 각 실행에서 첫 쓰기 직후 중단하고, PostgreSQL의 지급 요청 행과 로컬 체인의 트랜잭션 또는 영수증을 별도로 확인한다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Ethereum 개발 네트워크](https://ethereum.org/developers/docs/development-networks/) · [Ethereum eth_getTransactionReceipt](https://ethereum.org/developers/docs/apis/json-rpc/#eth-gettransactionreceipt)
