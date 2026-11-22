# Documenting GraphQL APIs with Introspection

Introspection은 같은 그래프에서 스키마의 타입·필드·설명·폐기 정보를 조회하는 표준 기능이다. IDE 자동 완성과 스키마 검사에 활용할 수 있다. [GraphQL · Introspection](https://graphql.org/learn/introspection/) · [GraphQL · September 2025 Specification](https://spec.graphql.org/September2025/) · [Apollo Server · Getting Started](https://www.apollographql.com/docs/apollo-server/getting-started)

## 1. 조회 중인 스키마에서 타입과 필드 정보를 읽는다

첫 서버에 아래 연산을 보내 Query의 필드와 설명을 확인한다. __schema는 전체 스키마를 탐색할 때, __typename은 객체의 런타임 타입을 판단할 때 쓴다. SDL에 문서 설명과 @deprecated 이유를 적어 팀이 같은 계약을 보게 한다. [GraphQL · Introspection](https://graphql.org/learn/introspection/) · [GraphQL · Schemas and Types](https://graphql.org/learn/schema/) · [Apollo Server · Directives](https://www.apollographql.com/docs/apollo-server/schema/directives)

```graphql
query InspectQuery {
  __type(name: "Query") {
    name
    fields(includeDeprecated: true) {
      name
      description
      isDeprecated
      deprecationReason
    }
  }
}
```

## 2. 공개 정책과 개발 문서화 경로를 정한다

Apollo Server는 기본적으로 NODE_ENV=production일 때 introspection을 비활성화한다. 환경 정책을 명시하고 배포된 SDL 또는 스키마 레지스트리에서 개발자가 계약을 볼 수 있게 한다. 접근 통제와 연산 비용 제한도 별도로 적용한다. [Apollo Server · ApolloServer API](https://www.apollographql.com/docs/apollo-server/api/apollo-server) · [GraphQL · Authorization](https://graphql.org/learn/authorization/) · [GraphQL · Security](https://graphql.org/learn/security/)
