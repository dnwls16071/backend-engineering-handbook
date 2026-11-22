# Implementing the TCC Order API

주문 접수 API는 호출자의 멱등 키와 주문 ID를 연결하고, 같은 키를 재사용했을 때 같은 접수 건을 찾을 수 있게 한다. [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/)

## 1. 접수 응답과 확정 상태를 분리한다

비동기 접수라면 주문·멱등 키·처리 의도를 커밋한 뒤 202 Accepted를 보내고 응답에 주문 ID와 상태 조회 URI를 안내한다. 동일한 호출자·키가 다른 상품 또는 수량으로 들어오면 409 Conflict로 처리하는 계약을 둘 수 있다. [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 2. 재요청과 상태 조회를 동일한 주문으로 연결한다

GET 주문 조회는 진행 상태와 갱신 시각을 반환한다. 클라이언트가 접수 응답을 잃었으면 같은 멱등 키로 다시 요청하고, 새 분기 키를 만들기 전에 이미 접수된 주문을 찾아 반환한다. [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted) · [AWS · Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/)
