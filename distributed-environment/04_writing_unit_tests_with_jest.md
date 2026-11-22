# Writing Unit Tests with Jest

주문 서비스가 사용하는 재고 조회 함수를 주입하고, 실제 네트워크 없이 주문 가능 여부와 의존성 실패를 검사한다. [Jest 30 · Getting Started](https://jestjs.io/docs/30.0/getting-started) · [Jest 30 · Mock Function API](https://jestjs.io/docs/30.0/mock-function-api)

## 1. Jest를 설치하고 Node 테스트 환경을 사용한다

빈 실습 디렉터리에서 Jest 버전을 고정하고 아래 설정을 jest.config.cjs에 저장한다. 이후 테스트 파일을 추가하고 npm test로 실행한다. [Jest 30 · Getting Started](https://jestjs.io/docs/30.0/getting-started) · [Jest 30 · Configuration](https://jestjs.io/docs/30.0/configuration#testenvironment-string)

```bash
npm init -y
npm install --save-dev --save-exact jest@30.2.0
npm pkg set 'scripts.test=jest'
```

```javascript
// jest.config.cjs
module.exports = { testEnvironment: 'node' };
```

## 2. 정상 결과와 재고 조회 실패를 검사한다

아래 코드 블록을 order-policy.test.cjs로 저장한다. 학습 예제에서는 함수와 테스트를 한 파일에 배치한다. 각 테스트는 대역을 새로 만들고, 비동기 단언을 await해 실패를 Jest가 관측하게 한다. [Jest 30 · Mock Function API](https://jestjs.io/docs/30.0/mock-function-api) · [Jest 30 · Asynchronous Code](https://jestjs.io/docs/30.0/asynchronous)

```javascript
// order-policy.test.cjs
async function canPlaceOrder(findAvailable, sku, quantity) {
  if (!Number.isSafeInteger(quantity) || quantity <= 0) {
    throw new RangeError('quantity must be a positive integer');
  }
  const available = await findAvailable(sku);
  return available >= quantity;
}

test('allows an order when the available quantity is sufficient', async () => {
  const findAvailable = jest.fn().mockResolvedValue(3);

  await expect(canPlaceOrder(findAvailable, 'sku-1', 3)).resolves.toBe(true);
  expect(findAvailable).toHaveBeenCalledWith('sku-1');
});

test('declines when stock is below the requested quantity', async () => {
  const findAvailable = jest.fn().mockResolvedValue(2);

  await expect(canPlaceOrder(findAvailable, 'sku-1', 3)).resolves.toBe(false);
});

test('rejects invalid input before querying stock', async () => {
  const findAvailable = jest.fn();

  await expect(canPlaceOrder(findAvailable, 'sku-1', 0)).rejects.toThrow(RangeError);
  expect(findAvailable).not.toHaveBeenCalled();
});

test('reports an unavailable inventory dependency', async () => {
  const failure = new Error('inventory unavailable');
  const findAvailable = jest.fn().mockRejectedValue(failure);

  await expect(canPlaceOrder(findAvailable, 'sku-1', 3)).rejects.toBe(failure);
});
```

## 3. 단위 테스트가 보장하는 범위를 읽는다

이 예로 확인하는 것은 수량 정책과 조회 실패의 전달이다. 조회 성공 직후 다른 주문이 같은 재고를 가져갈 수 있으므로 실제 예약의 동시성은 저장소에서 원자적으로 처리하고 통합 테스트에서 검증한다. [Jest 30 · Mock Function API](https://jestjs.io/docs/30.0/mock-function-api) · [Ham Vocke · The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) · [Microsoft · Microservice Data Considerations](https://learn.microsoft.com/en-us/azure/architecture/microservices/design/data-considerations)
