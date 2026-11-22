# Understanding Try-Confirm-Cancel

TCC 참가자는 Try로 자원을 예약하고, 조정자가 기록한 결정에 따라 Confirm 또는 Cancel을 적용한다. 각 호출은 참가자 내부에서 짧은 로컬 트랜잭션으로 처리한다. [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/)

## 1. 예약 수명과 참가 상태를 정의한다

| 단계 | 재고 | 포인트 | 근거 |
| --- | --- | --- | --- |
| Try | 가용 수량에서 예약 수량으로 옮긴다. | 가용 잔액에서 보류 잔액으로 옮긴다. | [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) |
| Confirm | 예약 수량을 확정 소비한다. | 보류 잔액을 정산하고 확정 차감을 기록한다. | [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) |
| Cancel | 가용 수량으로 반납한다. | 보류 금액을 가용 잔액으로 돌린다. | [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) |

## 2. 늦은 요청을 포함해 분기 계약을 만든다

예약이 끝날 때까지 DB 잠금을 열어 두는 대신 커밋된 업무 상태가 가용량을 제한한다. 같은 분기 키의 중복 호출을 허용하고, Cancel이 앞서면 취소 표시를 저장해 늦게 온 Try를 차단한다. [Apache Seata 2.4 · TCC Mode](https://seata.apache.org/docs/v2.4/user/mode/tcc/) · [Apache Seata · TCC Fence](https://seata.apache.org/blog/seata-tcc-fence/) · [MySQL 8.4 · Locking Reads](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html)
