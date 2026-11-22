# Understanding GraphQL and Its Type System

GraphQL은 클라이언트가 연산 문서로 필요한 필드를 선택하고 서버가 스키마를 기준으로 검증·실행하는 방식이다. 같은 게시글에서도 목록 화면과 상세 화면의 선택 집합이 다를 수 있다. [GraphQL · September 2025 Specification](https://spec.graphql.org/September2025/) · [GraphQL · Queries](https://graphql.org/learn/queries/) · [GraphQL · Schemas and Types](https://graphql.org/learn/schema/)

## 1. 스키마 문서와 연산 문서의 역할을 구분한다

SDL로 객체·스칼라·입력 타입, 필드와 인자를 선언한다. 연산 문서에는 선택 집합, 변수, 프래그먼트가 들어간다. 서버는 실행 전 필드와 입력 타입을 검증하고, 실행에서 resolver로 선택한 값을 구한다. [GraphQL · Schemas and Types](https://graphql.org/learn/schema/) · [GraphQL · Queries](https://graphql.org/learn/queries/) · [GraphQL · Execution](https://graphql.org/learn/execution/)

## 2. Null과 리스트의 계약을 읽는다

Post는 null일 수 있고 Post!는 결과에 null을 허용하지 않는다. [Post!]!는 목록과 각 원소가 null일 수 없지만 빈 목록은 가능하다. Non-Null 필드 오류는 가까운 nullable 경계까지 전파되므로 데이터 보장과 오류 수용 범위를 함께 고려한다. [GraphQL · Schemas and Types](https://graphql.org/learn/schema/) · [GraphQL · September 2025 Specification](https://spec.graphql.org/September2025/)

## 3. 주제별로 이어 읽기

[첫 Apollo 실습](03_starting_a_graphql_api_with_apollo_server.md), [블로그 스키마](05_organizing_a_graphql_blog_project.md), [Prisma 초기화](07_migrating_a_blog_database_with_prisma.md), [요청별 DataLoader](10_batching_graphql_resolvers_with_dataloader.md), [연결 페이지네이션](11_paginating_graphql_connections_with_cursors.md), [Federation](15_designing_federated_graphql_subgraphs.md) 순서로 연결한다. [Apollo Server · Getting Started](https://www.apollographql.com/docs/apollo-server/getting-started) · [Prisma ORM 6 · Migrate Workflows](https://www.prisma.io/docs/orm/v6/prisma-migrate/workflows/development-and-production) · [GraphQL · DataLoader](https://github.com/graphql/dataloader/tree/v2.2.3) · [Relay · GraphQL Cursor Connections](https://relay.dev/graphql/connections.htm) · [Apollo Federation · Entities](https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/entities/intro)
