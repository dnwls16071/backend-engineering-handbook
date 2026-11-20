# Valkey Persistence, Memory, and High Availability

재시작 후 데이터를 복구하는 영속성, 메모리 한도를 관리하는 퇴출, 노드 장애 시 서비스를 이어가는 고가용성은 각각 다른 문제를 해결한다.

## 1. RDB와 AOF 복구

| 방식 | 저장 내용 | 확인할 위험 |
| --- | --- | --- |
| RDB | 특정 시점의 데이터 전체를 스냅샷으로 저장한다. | 마지막 스냅샷 이후의 변경이 빠질 수 있다. |
| AOF | 쓰기 명령을 기록하고 재시작 시 재생한다. | `fsync` 정책에 따라 마지막 쓰기가 유실될 수 있고, 재작성 시 자원이 필요하다. |

일반적인 RDB 백그라운드 저장은 fork와 Copy-on-Write로 메모리와 지연에 영향을 줄 수 있다. Valkey 9.2에는 별도로 설정할 수 있는 forkless 스냅샷 방식이 있다. AOF의 `everysec`은 약 1초 주기의 동기화 정책이며, 예상치 못한 장애에서 직전 변경이 빠질 수 있다. RDB와 AOF가 함께 활성화되어 있으면 재시작 시 AOF를 사용한다. 복구 가능성을 확인하려면 파일 보유 여부와 함께 복원 후 실제 키와 TTL을 검증한다. [Persistence](https://valkey.io/topics/persistence/) · [Valkey 9.2](https://valkey.io/download/9.2/)

아래는 실습용 이름 있는 볼륨에 각각 저장한 뒤 재시작하는 예제다. `SAVE`는 데이터가 작은 실습에서만 사용한다. 일반 운영에서 스냅샷을 생성할 때는 `BGSAVE`와 `INFO persistence`를 사용해 작업 완료를 확인한다.

```bash
docker run -d --name valkey-rdb-lab --network none \
  -v valkey-lab-rdb:/data valkey/valkey:9.2.0 \
  valkey-server --save "" --appendonly no
docker exec valkey-rdb-lab valkey-cli SET lab:rdb snapshot
docker exec valkey-rdb-lab valkey-cli SAVE
docker restart valkey-rdb-lab
docker exec valkey-rdb-lab valkey-cli GET lab:rdb

docker run -d --name valkey-aof-lab --network none \
  -v valkey-lab-aof:/data valkey/valkey:9.2.0 \
  valkey-server --save "" --appendonly yes --appendfsync everysec
docker exec valkey-aof-lab valkey-cli SET lab:aof replay
docker restart valkey-aof-lab
docker exec valkey-aof-lab valkey-cli GET lab:aof
```

재시작 직후 로딩 중이면 `PING`이 성공한 뒤 조회한다. 이 예제의 정상 재시작은 쓰기 손실 가능 구간을 측정하는 장애 시험과는 목적이 다르다.

## 2. Maxmemory, eviction, Big Key, Hot Key

`maxmemory` 한도에 도달할 때 `allkeys-lru`·`allkeys-lfu`는 모든 키를 후보로 고르고, `volatile-*` 정책은 TTL이 있는 키를 후보로 고른다. `volatile-*`에 퇴출 후보가 없거나 `noeviction`을 쓰면 메모리를 더 쓰는 명령이 거절될 수 있다. 원본이 있는 캐시와 지속 보관할 데이터에 같은 퇴출 정책을 적용할지는 별도로 판단한다. [Key eviction](https://valkey.io/topics/lru-cache/)

```bash
vk CONFIG GET maxmemory maxmemory-policy
vk INFO memory
vk INFO stats | rg '^(evicted_keys|expired_keys):'
vk MEMORY USAGE lab:cart:42
docker exec valkey-lab valkey-cli --bigkeys -i 0.1
```

Big Key는 값의 크기나 원소 개수가 커서 메모리·전송·명령 시간을 많이 쓰는 키다. `--bigkeys`는 타입별 큰 후보를 찾고 `MEMORY USAGE`는 해당 키의 메모리 비용을 확인하는 데 쓴다. Hot Key는 값이 작아도 요청이 집중되는 키다. Valkey 9.2에서 `hotkeys-top-k`가 기본값 0이면 서버 추적이 꺼져 있다. 샘플링을 켠 뒤 여러 보고 구간에 걸쳐 실제 요청을 관찰하면 `HOTKEYS GET`에서 마지막으로 완료한 구간의 근사 후보를 볼 수 있다. 아래 명령은 실습 노드에서 실행한다. [Valkey CLI](https://valkey.io/topics/cli/) · [Hot key tracking](https://valkey.io/topics/hotkeys/)

```bash
vk CONFIG GET 'hotkeys-*'
vk CONFIG SET hotkeys-top-k 5 hotkeys-sampling-percentage 100
# 다른 터미널에서 요청을 실행하면서 보고 구간이 지난 뒤 확인한다.
vk HOTKEYS GET
vk CONFIG SET hotkeys-top-k 0 hotkeys-sampling-percentage 1
```

## 3. 비동기 복제와 Sentinel 자동 승격

프라이머리·레플리카 복제는 기본적으로 비동기다. 레플리카가 아직 받지 못한 쓰기가 있으면 장애 조치 후 최신 데이터가 빠질 수 있다. Sentinel은 프라이머리 장애 판단, 레플리카 승격, 클라이언트의 새 프라이머리 발견을 담당한다. 아래 실습은 같은 Docker 네트워크에 데이터 노드 2개와 Sentinel 3개를 둔다. 운영에서는 장애 도메인도 분리한다. [Replication](https://valkey.io/topics/replication/) · [Sentinel](https://valkey.io/topics/sentinel/)

```bash
docker network create valkey-ha-lab

docker run -d --name valkey-ha-primary --network valkey-ha-lab \
  valkey/valkey:9.2.0 valkey-server --save "" --appendonly no \
  --replica-announce-ip valkey-ha-primary

docker run -d --name valkey-ha-replica --network valkey-ha-lab \
  valkey/valkey:9.2.0 valkey-server --save "" --appendonly no \
  --replicaof valkey-ha-primary 6379 --replica-announce-ip valkey-ha-replica

for suffix in 1 2 3; do
  sentinel="valkey-ha-sentinel-$suffix"
  docker run -d --name "$sentinel" --hostname "$sentinel" \
    --network valkey-ha-lab --entrypoint sh valkey/valkey:9.2.0 -ec '
      printf "%s\n" \
        "port 26379" \
        "sentinel resolve-hostnames yes" \
        "sentinel announce-hostnames yes" \
        "sentinel announce-ip $(hostname)" \
        "sentinel monitor cache-primary valkey-ha-primary 6379 2" \
        "sentinel down-after-milliseconds cache-primary 3000" \
        "sentinel failover-timeout cache-primary 15000" > /data/sentinel.conf
      exec valkey-server /data/sentinel.conf --sentinel
    '
done
```

세 Sentinel이 서로를 발견하고 `SENTINEL CKQUORUM`이 성공할 때까지 확인한다. Quorum 2는 객관적 장애 판정에 필요한 동의 수다. 자동 승격을 수행하는 Sentinel은 별도로 Sentinel 과반수의 승인을 받아야 한다. `WAIT`은 같은 연결에서 이전 쓰기가 레플리카에 도달했는지 실습으로 확인한다.

```bash
docker exec valkey-ha-sentinel-1 valkey-cli -p 26379 \
  SENTINEL CKQUORUM cache-primary

docker exec -i valkey-ha-primary valkey-cli --raw <<'COMMANDS'
SET lab:failover ready
WAIT 1 5000
COMMANDS

docker stop valkey-ha-primary
docker exec valkey-ha-sentinel-1 valkey-cli -p 26379 \
  SENTINEL get-master-addr-by-name cache-primary
docker exec valkey-ha-replica valkey-cli ROLE
docker exec valkey-ha-replica valkey-cli GET lab:failover
```

몇 초 간격으로 다시 조회하면 프라이머리 주소가 `valkey-ha-replica`로 바뀌고 그 노드가 쓰기를 받을 수 있다. 운영 클라이언트는 Sentinel 이름과 주소 목록으로 접속하고, 재연결 시 새 프라이머리를 다시 발견한다. `WAIT` 성공도 영속화나 장애 후 무손실을 보장하지 않는다. [WAIT](https://valkey.io/commands/wait/) · [Sentinel 클라이언트 사양](https://valkey.io/topics/sentinel-clients/)
