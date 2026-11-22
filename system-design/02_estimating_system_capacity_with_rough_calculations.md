# Estimating System Capacity with Rough Calculations

요청 수, 데이터 크기, 보존 기간을 먼저 추정하고 피크와 장애 여유를 더한다. 아래 수치는 실측 전 가정이다. 실제 처리 용량은 요청 유형과 장애 조건을 넣은 부하 시험에서 구한다. [Google SRE · Handling Overload](https://sre.google/sre-book/handling-overload/) · [Google SRE · Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)

## 1. 평균과 피크 요청 수를 계산한다

DAU 1,000,000명, 사용자당 하루 읽기 20건이면 하루 20,000,000건이다. 86,400초로 나누면 평균 약 231 RPS다. 피크가 평균의 5배라면 약 1,157 RPS를 시작점으로 삼는다. 쓰기 2건/사용자/일이라면 평균 약 23 RPS다. [Google SRE · Handling Overload](https://sre.google/sre-book/handling-overload/)

## 2. 보존 용량과 응답 대역폭을 계산한다

쓰기 2,000,000건/일에 1 KiB씩 저장하면 약 2.05 GB/일이다. 30일은 약 61.44 GB이며, 사본 3개면 약 184.32 GB다. 이 계산에서 인덱스, 백업, 메타데이터와 압축 효과는 별도 항목이다. [Google SRE · Handling Overload](https://sre.google/sre-book/handling-overload/) · [Amazon · Dynamo](https://www.amazon.science/publications/dynamo-amazons-highly-available-key-value-store)

피크 읽기 1,160 RPS에서 응답이 평균 8 KiB면 약 9.1 MiB/s의 응답 본문을 전송한다. 8 KiB는 본문만의 가정이며 헤더, 내부 서비스 간 전송과 재시도를 별도로 측정한다. [Google SRE · Handling Overload](https://sre.google/sre-book/handling-overload/) · [Google SRE · Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)

## 3. 가정을 실험으로 좁힌다

인스턴스 한 대가 SLO 안에서 버티는 RPS를 먼저 구한다. 피크 예상치에 이 용량을 적용한 뒤 장애로 인스턴스가 하나 빠졌을 때도 요청·DB·큐의 한도가 지켜지는지 확인한다. 요청 크기와 캐시 적중률을 달리하면 측정값의 민감도를 알 수 있다. [Google SRE · Implementing SLOs](https://sre.google/workbook/implementing-slos/) · [Google SRE · Handling Overload](https://sre.google/sre-book/handling-overload/) · [Google SRE · Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)

## 4. 피크 추정을 인스턴스 수와 적체 시간으로 바꾼다

부하 시험에서 한 대가 SLO를 지키며 읽기 320 RPS를 처리했다고 가정한다. 피크 1,160 RPS에는 올림 계산으로 최소 4대가 필요하다. 한 대가 빠져도 버티려면 5대를 배치하고, 나머지 4대로 1,160 RPS를 보낼 때 공유 DB와 캐시도 SLO를 지키는지 시험한다. [Google SRE · Implementing SLOs](https://sre.google/workbook/implementing-slos/) · [Google SRE · Handling Overload](https://sre.google/sre-book/handling-overload/)

비동기 작업이 120초간 초당 1,500건 들어오고 작업자가 초당 1,000건을 처리하면 60,000건이 밀린다. 이후 유입이 초당 700건으로 내려가면 초당 300건씩 줄어 적체를 비우는 데 약 200초가 걸린다. 처리율이 일정하다는 가정으로 얻은 복구 시간이다. 가장 오래 기다린 작업의 체류 시간은 따로 측정해 사용자 기한과 비교한다. [Google SRE · Handling Overload](https://sre.google/sre-book/handling-overload/) · [Google SRE · Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
