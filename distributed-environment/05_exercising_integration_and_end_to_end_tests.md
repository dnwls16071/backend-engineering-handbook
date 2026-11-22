# Exercising Integration and End-to-End Tests

통합 테스트에서는 실제 어댑터와 의존성을 연결하고, 종단 간 테스트에서는 배포된 사용자 진입점부터 업무 완료 상태를 확인한다. [Ham Vocke · The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)

## 1. 실제 HTTP 요청을 보내는 어댑터 통합 테스트

Node와 Jest 30.2.0을 준비하고 다음 블록을 inventory-http.test.cjs에 저장한 뒤 npx jest --runInBand inventory-http.test.cjs를 실행한다. 테스트가 실제 로컬 포트를 사용하며, 서버 구현은 테스트용 응답을 돌려준다. [Jest 30 · Getting Started](https://jestjs.io/docs/30.0/getting-started) · [Node.js 22 · HTTP](https://nodejs.org/download/release/v22.21.1/docs/api/http.html) · [Node.js 22 · Net](https://nodejs.org/download/release/v22.21.1/docs/api/net.html) · [Node.js 22 · Fetch](https://nodejs.org/download/release/v22.21.1/docs/api/globals.html#fetch)

```javascript
// inventory-http.test.cjs
const { createServer } = require('node:http');

let server;
let baseUrl;

beforeAll(async () => {
  server = createServer((request, response) => {
    if (request.method === 'GET' && request.url === '/inventory/sku-1') {
      response.writeHead(200, { 'content-type': 'application/json' });
      response.end(JSON.stringify({ available: 3 }));
      return;
    }
    response.writeHead(404).end();
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

afterAll(async () => {
  if (!server?.listening) return;
  await new Promise((resolve, reject) => {
    server.close((error) => error ? reject(error) : resolve());
  });
});

async function readAvailable(sku) {
  const response = await fetch(`${baseUrl}/inventory/${encodeURIComponent(sku)}`);
  if (!response.ok) throw new Error(`inventory HTTP ${response.status}`);
  const stock = await response.json();
  return stock.available;
}

test('decodes the real HTTP response', async () => {
  await expect(readAvailable('sku-1')).resolves.toBe(3);
});

test('keeps a missing SKU distinguishable from zero stock', async () => {
  await expect(readAvailable('missing')).rejects.toThrow('inventory HTTP 404');
});
```

## 2. DB 통합 테스트에서 운영과 같은 제약을 적용한다

예를 들어 PostgreSQL 컨테이너에서 실제 마이그레이션을 적용한 뒤 같은 주문 ID로 두 예약을 병렬 실행한다. 예약이 한 건만 남는지 DB로 확인한다. CI 작업 간 테스트 데이터가 섞이지 않도록 데이터베이스나 이 테스트가 쓰는 식별자를 격리한다. [Testcontainers for Node.js · PostgreSQL](https://node.testcontainers.org/modules/postgresql/) · [Ham Vocke · The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)

## 3. 종단 간 테스트에서 사용자 진입점부터 확인한다

격리된 배포 환경의 공개 주문 API에 요청을 보내고 상태 조회로 주문과 예약이 완료됐는지 확인한다. 비동기 흐름에는 기한이 있는 폴링을 사용하며, 완료되지 않았으면 주문 ID와 마지막 관찰 상태를 남긴다. 배포된 주문 API, 예약 서비스, 저장소, 메시지 경로가 함께 참여한다. [Ham Vocke · The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)

실습에서는 (1) 테스트 전용 SKU를 준비하고, (2) 주문 제출의 응답으로 받은 ID를 기준으로 완료 상태까지 조회하고, (3) 재고가 요청 수량만큼 한 번 줄었는지 검증한다. 실패 시 요청 ID, 마지막 조회 응답, 환경의 서비스 버전을 함께 기록한다. [Ham Vocke · The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) · [OpenTelemetry · Context Propagation](https://opentelemetry.io/docs/concepts/context-propagation/)
