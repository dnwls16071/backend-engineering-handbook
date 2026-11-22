# 데이터 흐름에 실패 지점부터 표시하기

## 1. 경계마다 남길 영속 증거를 고른다

접수의 증거는 PostgreSQL의 `payout_request`와 `outbox`다. 제출 직전에는 `payout_attempt`에 거래 식별자를 남기고, 외부 결과는 해당 거래 해시의 영수증과 블록을 바탕으로 확인한다. 업무 상태 변화는 `payout_status_history`로 추적한다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Ethereum eth_sendRawTransaction](https://ethereum.org/developers/docs/apis/json-rpc/#eth-sendrawtransaction) · [Ethereum eth_getTransactionReceipt](https://ethereum.org/developers/docs/apis/json-rpc/#eth-gettransactionreceipt)

## 2. 다음 작업이 실패하면 이어갈 위치를 고른다

접수 커밋 뒤 Relay가 멈추면 미발행 Outbox가 다시 시작할 위치다. Queue에 전달하고 발행 표시 전에 멈추면 같은 이벤트가 다시 올 수 있다. 송금 제출 후 응답이 유실되면 기존 시도를 확인하고, 확인 결과를 DB에 반영하기 전에 중단되면 Confirmer가 같은 해시를 다시 조회한다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [AWS 타임아웃과 재시도](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) · [Ethereum eth_getTransactionReceipt](https://ethereum.org/developers/docs/apis/json-rpc/#eth-gettransactionreceipt)

![외부 작업 직전과 직후에 실패를 주입해 어느 기록이 남는지 확인하는 두 쓰기 경계](image/01_dual_write.png)

그림의 근거 · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 3. 장애별로 복구 후 관측할 값을 적는다

로컬 체인에서 접수 직후, Queue 전달 직후, RPC 응답 수신 직전에 각각 Worker나 해당 컴포넌트를 멈춘다. 요청별 Outbox와 시도, 외부 영수증을 연결해 누락과 중복을 찾고, 결과가 불명확한 시도가 `FAILED`나 `COMPLETED`로 성급히 바뀌지 않는지 확인한다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [AWS 타임아웃과 재시도](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) · [Ethereum eth_getTransactionReceipt](https://ethereum.org/developers/docs/apis/json-rpc/#eth-gettransactionreceipt) · [Ethereum 개발 네트워크](https://ethereum.org/developers/docs/development-networks/)
