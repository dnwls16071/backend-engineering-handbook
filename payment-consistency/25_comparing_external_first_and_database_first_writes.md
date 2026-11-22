# 외부 우선 Dual Write를 DB 우선과 비교하기

## 1. 외부 제출 뒤 요청을 저장하는 실습 경로를 만든다

두 순서를 비교하기 위해 외부 우선 경로에서는 `payout_id`를 메모리에서 만들고 로컬 Ethereum RPC에 서명 거래를 제출한 다음 `payout_request`와 `payout_attempt`를 저장한다. 전송 전에 시도와 해시를 커밋하는 일반 Worker 경로와 다른 장애를 관찰하는 실습이다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Ethereum RPC 전송](https://ethereum.org/developers/docs/apis/json-rpc/#eth-sendrawtransaction) · [PostgreSQL 18 트랜잭션](https://www.postgresql.org/docs/18/tutorial-transactions.html)

```text
existing = check_idempotency_key(merchant, key, normalized_body)
if existing:
    return existing.original_accept_response

payout_id = create_local_id()
signed = prepare_and_sign(payout_id, normalized_body)
hash = submit_to_local_rpc(signed)
fail_if_enabled("after_rpc_accept")
return commit_payout_and_attempt(payout_id, key, hash)
```

## 2. 외부 제출이 수락된 직후 저장 실패를 주입한다

Anvil이 서명 거래를 수락한 뒤 DB 저장 직전에 예외를 던진다. 같은 시나리오를 트랜잭션 내부에서 실패시켜 롤백 결과도 확인한다. 채굴한 블록에서 영수증과 수신인 잔액을 확인하면 DB 요청 영 건과 외부 지급 한 건을 관찰할 수 있다. DB의 멱등 키가 저장되지 않기 때문에, 다음 API 호출이 같은 키로 별도 nonce의 지급을 시작하면 외부 지급이 두 번 발생할 수 있다. [Foundry Anvil 명령](https://www.getfoundry.sh/reference/anvil/anvil) · [Ethereum RPC 영수증](https://ethereum.org/developers/docs/apis/json-rpc/#eth-gettransactionreceipt) · [Ethereum 트랜잭션](https://ethereum.org/en/developers/docs/transactions/) · [PostgreSQL 18 트랜잭션](https://www.postgresql.org/docs/18/tutorial-transactions.html) · [AWS 멱등 재시도 설계](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 3. 어떤 증거로 복구할 수 있는지 비교한다

DB 우선의 대표 실패에는 지급 의도가 남으므로 요청과 시도 유무를 대조해 후속 단계를 복구할 수 있다. 외부 우선의 대표 실패에는 내부 식별자와 온체인 해시의 연결이 유실될 수 있으므로 재전송에 앞서 외부 실행 사실을 찾아야 한다. 실습 시에는 테스트 도구가 관측한 해시로 불일치를 검증하고, 복구 절차에는 미리 커밋한 식별자가 필요하다는 점을 확인한다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [AWS 멱등 재시도 설계](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Ethereum RPC 전송](https://ethereum.org/developers/docs/apis/json-rpc/#eth-sendrawtransaction) · [Ethereum RPC 영수증](https://ethereum.org/developers/docs/apis/json-rpc/#eth-gettransactionreceipt)

양쪽 실습을 나란히 실행해 장애 지점, 요청 행·시도 행 수, 영수증, 잔액 차이를 기록한다. 같은 키를 재호출한 횟수와 실제 지급 수를 별도로 센다. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [AWS 멱등 재시도 설계](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Ethereum RPC 영수증](https://ethereum.org/developers/docs/apis/json-rpc/#eth-gettransactionreceipt)

![DB 우선과 외부 우선에서 첫 번째 쓰기 뒤 실패할 때 남는 상태를 비교한 그림](image/01_dual_write.png)
