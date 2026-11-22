# Using GraphQL Operations and Directives

Query·Mutation·Subscription은 각각 조회, 상태 변경, 이벤트에 따른 응답 흐름을 표현한다. 채택한 HTTP 또는 WebSocket 계약은 연산의 실행 의미와 분리해서 정한다. [GraphQL · September 2025 Specification](https://spec.graphql.org/September2025/) · [GraphQL · Queries](https://graphql.org/learn/queries/) · [GraphQL over HTTP · Draft](https://graphql.github.io/graphql-over-http/draft/) · [Apollo Server · Subscriptions](https://www.apollographql.com/docs/apollo-server/data/subscriptions)

## 1. 연산별 실행 흐름을 이해한다

| 연산 | 주요 의미 | 근거 |
| --- | --- | --- |
| Query | 필드의 값을 조회한다. 루트 필드가 특정 순서로 실행된다고 가정하지 않는다. | [GraphQL · September 2025 Specification](https://spec.graphql.org/September2025/) · [GraphQL · Execution](https://graphql.org/learn/execution/) |
| Mutation | 상태 변경을 요청한다. 한 연산 안의 최상위 mutation 필드는 직렬로 실행된다. | [GraphQL · September 2025 Specification](https://spec.graphql.org/September2025/) · [GraphQL · Execution](https://graphql.org/learn/execution/) |
| Subscription | 선택한 이벤트 소스를 구독한다. 한 연산에 허용되는 루트 구독 필드 수는 하나다. | [GraphQL · September 2025 Specification](https://spec.graphql.org/September2025/) · [Apollo Server · Subscriptions](https://www.apollographql.com/docs/apollo-server/data/subscriptions) |

## 2. Directive가 적용되는 위치와 구현을 확인한다

연산의 @include와 @skip은 조건에 따라 필드를 고른다. 스키마의 @deprecated는 계약 변경 계획을 알린다. @auth 같은 사용자 정의 directive를 SDL에 적는 것만으로는 인가 로직이 실행되지 않는다. resolver나 스키마 변환과 함께 적용하되 업무 정책은 서비스에서도 강제한다. [GraphQL · September 2025 Specification](https://spec.graphql.org/September2025/) · [Apollo Server · Directives](https://www.apollographql.com/docs/apollo-server/schema/directives) · [GraphQL · Authorization](https://graphql.org/learn/authorization/)
