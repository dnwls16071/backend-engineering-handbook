# 지급 생성 API의 DB 우선 Dual Write 실습

## 1. 검증과 요청 커밋을 먼저 실행한다

`POST /payouts`에서 가맹점 권한, 자산, 수신인, 최소 단위 금액을 확인하고 `Idempotency-Key` 충돌을 검사한다. 이 실습은 직접 전송의 장애를 관찰하기 위해 `payout_request`에 `ACCEPTED`를 커밋한 뒤 별도 단계에서 Worker 전송 함수를 호출한다. 이 경로에는 전송 의도를 보존하는 `outbox` 기록을 생략한다. [AWS 멱등 재시도 설계](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [PostgreSQL 18 제약](https://www.postgresql.org/docs/18/ddl-constraints.html) · [PostgreSQL 18 트랜잭션](https://www.postgresql.org/docs/18/tutorial-transactions.html) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

```text
request, created = commit_payout_request(merchant, key, normalized_body)
if created:
    fail_if_enabled("after_db_commit")
    attempt = commit_signed_attempt(request.payout_id)
    submit_signed_attempt(attempt)
return request.original_accept_response
```

## 2. 커밋과 Worker 호출 사이에서 실패시킨다

DB 트랜잭션 안에서 실패를 주입하면 생성 행이 롤백된다. 커밋이 성공한 직후, Worker 진입 전 예외를 던지면 `ACCEPTED` 요청과 최초 접수 응답이 남고 전송은 시작되지 않는다. 이 경로에서 같은 키를 재전송하면 기존 접수 결과가 반환되므로, 직접 전송을 다시 시작할 별도 복구 경로가 필요하다. [PostgreSQL 18 트랜잭션](https://www.postgresql.org/docs/18/tutorial-transactions.html) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [AWS 멱등 재시도 설계](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

또 다른 실행에서는 시도·해시를 기록한 뒤 로컬 노드에게 서명 거래를 넘기고 응답만 끊는다. 이번에는 같은 DB 요청과 시도가 남고, 블록 채굴 뒤 RPC에서 지급을 관측할 수 있다. 저장된 해시로 두 장애를 구분한다. [Ethereum RPC 전송](https://ethereum.org/developers/docs/apis/json-rpc/#eth-sendrawtransaction) · [Ethereum RPC 영수증](https://ethereum.org/developers/docs/apis/json-rpc/#eth-gettransactionreceipt) · [AWS 타임아웃과 재시도](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)

## 3. 행 수와 외부 지급을 함께 검증한다

로컬 DB와 Anvil을 사용해 정상 실행, 커밋 전 예외, 커밋 직후 예외, 제출 응답 유실을 순서대로 실행한다. 실행마다 새 키와 별도 초기 상태를 사용해 요청·시도 행 수 및 수신인 잔액 변화와 영수증을 기록한다. DB 우선 경로에서 측정할 대표 불일치는 요청 한 건과 외부 지급 영 건이다. [PostgreSQL 18 트랜잭션](https://www.postgresql.org/docs/18/tutorial-transactions.html) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) · [Ethereum RPC 영수증](https://ethereum.org/developers/docs/apis/json-rpc/#eth-gettransactionreceipt) · [Foundry Anvil 명령](https://www.getfoundry.sh/reference/anvil/anvil)

![DB 커밋을 먼저 실행했을 때 다음 외부 호출에 도달하기 전에 실패하는 구간](image/01_dual_write.png)
