# Redis Server Setup and Deployment Topologies

Redis 서버를 띄울 때는 접속 주소, 포트, 데이터 복구 방식을 먼저 정한다. 단일 인스턴스로 연결과 설정을 확인한 뒤, 복제와 자동 장애 조치, 여러 서버에 데이터를 나누는 구성을 비교한다.

## 1. 실습용 Standalone 서버 실행

`redis-server`와 `redis-cli`가 설치된 환경에서 다음 명령을 실행한다. 임시 디렉터리와 루프백 주소를 사용해 실습 서버를 다른 인스턴스와 분리한다. 포트가 사용 중이면 설정과 뒤에 나오는 접속 명령에서 함께 바꾼다.

```sh
lab_dir="$(mktemp -d)"

cat > "$lab_dir/redis.conf" <<'CONF'
bind 127.0.0.1
port 16379
protected-mode yes
save ""
appendonly no
CONF

redis-server "$lab_dir/redis.conf" --dir "$lab_dir"
```

서버가 준비되면 다른 터미널에서 연결과 적용된 설정을 확인한다.

```sh
redis-cli -h 127.0.0.1 -p 16379 PING
redis-cli -h 127.0.0.1 -p 16379 CONFIG GET appendonly
redis-cli -h 127.0.0.1 -p 16379 INFO replication
```

`PING`에 `PONG`이 오면 접속된 것이다. `CONFIG GET`에서 `appendonly`가 `no`인지 확인하고, `INFO replication`에서 서버 역할과 연결된 복제본 수를 본다. 단일 서버는 `role:master`와 `connected_slaves:0`을 보고한다. 예제는 RDB 자동 저장과 AOF를 끈 상태로 실행한다.

**공식 문서** [Redis 구성 파일과 실행 옵션](https://redis.io/docs/latest/operate/oss_and_stack/management/config/) · [CONFIG GET](https://redis.io/docs/latest/commands/config-get/) · [INFO](https://redis.io/docs/latest/commands/info/)

## 2. 설정 파일에서 결정할 항목

| 항목 | 역할 |
| --- | --- |
| `bind`, `port` | 어떤 주소와 포트에서 요청을 받을지 지정한다. `127.0.0.1`은 같은 호스트에서의 접속에 사용한다. |
| `protected-mode` | 안전하지 않은 기본 설정에서 원격 연결을 제한하는 보호 모드다. 운영 환경의 접속 범위와 인증은 네트워크 설정과 Redis ACL로 관리한다. |
| `save` | RDB 스냅샷의 자동 저장 조건이다. 마지막 스냅샷 이후의 변경은 그 스냅샷에서 복구할 수 없다. |
| `appendonly`, `appendfsync` | AOF 사용 여부와 기록의 동기화 정책을 정한다. 복구 시 AOF에 기록된 변경을 적용한다. |
| `maxmemory`, `maxmemory-policy` | 데이터 메모리 한도에 도달했을 때 어떤 키를 제거하거나 쓰기를 거절할지 정한다. |

실행 중 일부 설정은 `CONFIG SET`으로 바꿀 수 있다. 변경을 재시작 이후에도 적용하려면 구성 파일에 반영한다. 파일로 시작한 서버는 `CONFIG REWRITE`를 사용해 현재 설정을 파일에 반영할 수도 있다.

**공식 문서** [Redis 구성 변경](https://redis.io/docs/latest/operate/oss_and_stack/management/config/) · [Redis 보안과 Protected Mode](https://redis.io/docs/latest/operate/oss_and_stack/management/security/) · [RDB와 AOF](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/) · [키 제거 정책](https://redis.io/docs/latest/develop/reference/eviction/)

## 3. 복제본 연결과 쓰기 전파 확인

앞서 실행한 서버를 유지한 채 새 터미널에서 `16380` 포트에 복제본을 띄운다. `--replicaof`에는 원본 서버의 주소와 포트를 지정한다.

```sh
replica_dir="$(mktemp -d)"
redis-server --bind 127.0.0.1 --port 16380 --protected-mode yes \
    --dir "$replica_dir" --save "" --appendonly no \
    --replicaof 127.0.0.1 16379
```

세 번째 터미널에서 복제본의 `INFO replication`을 확인한다. `master_link_status:up`과 `master_sync_in_progress:0`이 표시되면 Primary에 값을 쓴 뒤 Replica에서 읽는다.

```sh
redis-cli -h 127.0.0.1 -p 16380 INFO replication
redis-cli -h 127.0.0.1 -p 16379 SET lab:redis:role primary
redis-cli -h 127.0.0.1 -p 16380 GET lab:redis:role
```

Replica의 조회 결과는 `primary`다. 값이 아직 보이지 않으면 복제 상태를 확인한 뒤 다시 읽는다. Redis 복제는 비동기이므로 Primary에 쓰기가 성공해도 Replica에는 지연되어 반영될 수 있다. 최신 값이 필요한 읽기는 Primary에서 처리한다.

실습이 끝나면 복제본과 원본 서버를 실행한 각 터미널에서 `Ctrl+C`로 종료한다.

**공식 문서** [Redis 복제](https://redis.io/docs/latest/operate/oss_and_stack/management/replication/) · [REPLICAOF](https://redis.io/docs/latest/commands/replicaof/)

## 4. Standalone, Sentinel, Cluster 선택 기준

| 구성 | 쓰기 위치 | 선택 기준 |
| --- | --- | --- |
| Standalone | 단일 서버 | 개발 환경이나 데이터와 트래픽을 한 서버로 처리할 수 있는 환경 |
| Primary–Replica | Primary 한 대 | 복제본에 독립적인 읽기 경로가 필요하거나, 원본 장애 시 수동 전환할 구성이 필요한 환경 |
| Sentinel | 현재 Primary 한 대 | 단일 Primary로 용량과 쓰기 부하를 감당할 수 있고, 자동 장애 조치가 필요한 환경 |
| Redis Cluster | 키의 해시 슬롯을 담당하는 Primary | 메모리 용량이나 쓰기 부하를 여러 Primary로 분산해야 하는 환경 |

Sentinel은 비클러스터 구성의 Redis를 감시하고, Primary에 장애가 나면 Replica를 승격한다. Sentinel을 지원하는 클라이언트는 현재 Primary 주소를 조회하고 전환 후 다시 연결한다. 여러 Sentinel을 서로 독립적인 장애 영역에 배치하면 한 호스트 장애가 감시와 장애 조치에 동시에 영향을 주는 일을 줄일 수 있다.

Redis Cluster는 16,384개 해시 슬롯을 여러 Primary에 배분한다. 요청은 슬롯에 맞는 노드로 전달되므로 슬롯 관리와 리다이렉션을 지원하는 클라이언트가 필요하다. 각 Primary에 Replica를 추가하면 샤드별 장애 조치에 사용할 수 있다. [샤딩과 복제 동작](../cache/01_cache_fundamentals_and_redis_cluster.md)

**공식 문서** [Redis Sentinel](https://redis.io/docs/latest/operate/oss_and_stack/management/sentinel/) · [Redis Cluster 운영](https://redis.io/docs/latest/operate/oss_and_stack/management/scaling/) · [Redis Cluster 사양](https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/)
