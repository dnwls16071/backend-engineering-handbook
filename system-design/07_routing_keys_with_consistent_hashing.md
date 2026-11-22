# Routing Keys with Consistent Hashing

서버 수가 바뀔 때 키 매핑을 다시 계산해야 한다. 일관된 해싱은 변경된 노드 주변의 구간에 이동을 제한하도록 키와 노드 토큰을 같은 해시 공간에 둔다. [Karger 외 · Consistent Hashing](https://people.csail.mit.edu/karger/Papers/web.pdf) · [Amazon · Dynamo](https://www.amazon.science/publications/dynamo-amazons-highly-available-key-value-store)

## 1. 키와 노드를 같은 링에 배치한다

키의 해시값에서 시계 방향으로 첫 노드 토큰을 찾아 담당 노드를 고르는 예다. 이전 토큰과 다음 토큰 사이에 토큰을 추가하면 새 토큰이 직전 토큰 이후부터 자신까지의 구간을 가져간다. [Karger 외 · Consistent Hashing](https://people.csail.mit.edu/karger/Papers/web.pdf)

## 2. 가상 노드와 핫 키를 구분한다

물리 서버가 여러 토큰을 가지게 하면 배치 단위를 잘게 나눌 수 있다. 노드 수와 토큰 수가 균형을 이루더라도 특정 키가 매우 뜨거우면 그 키의 담당 노드에 요청이 몰릴 수 있다. [Amazon · Dynamo](https://www.amazon.science/publications/dynamo-amazons-highly-available-key-value-store) · [Google SRE · Handling Overload](https://sre.google/sre-book/handling-overload/)

## 3. 토폴로지 변경 중의 읽기와 쓰기를 정한다

토폴로지 버전을 배포하고 이동 대상 구간을 정한다. 캐시에서는 미스로 인한 원본 부하를, 원본 저장소에서는 데이터 이관과 이전·새 경로의 쓰기 정합성을 확인한다. 노드 추가 전후의 이동 비율과 최대 노드 부하를 측정한다. [Amazon · Dynamo](https://www.amazon.science/publications/dynamo-amazons-highly-available-key-value-store) · [Microsoft Cache-Aside](https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside) · [Google SRE · Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
