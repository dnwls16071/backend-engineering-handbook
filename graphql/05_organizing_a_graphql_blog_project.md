# Organizing a GraphQL Blog Project

블로그 실습은 공개 스키마, resolver, Prisma 스키마와 요청 컨텍스트를 분리한다. 사용자는 게시글을 조회하고, 인증된 작성자는 자신의 게시글을 생성·수정·삭제한다. [GraphQL · Schemas and Types](https://graphql.org/learn/schema/) · [GraphQL · Authorization](https://graphql.org/learn/authorization/) · [Prisma ORM 6 · Relations in Schema](https://www.prisma.io/docs/orm/v6/prisma-schema/data-model/relations)

## 1. GraphQL 스키마를 별도 파일에 둔다

아래를 blog.graphql에 저장한다. 이 확장자는 SDL을 담는 관례이며, 서버가 파일을 읽어 ApolloServer에 typeDefs로 전달해야 한다. 연결 페이지네이션을 위한 타입도 미리 선언한다. [GraphQL · Schemas and Types](https://graphql.org/learn/schema/) · [Relay · GraphQL Cursor Connections](https://relay.dev/graphql/connections.htm) · [Apollo Server · Getting Started](https://www.apollographql.com/docs/apollo-server/getting-started)

```graphql
# blog.graphql
type Author { id: ID!, name: String! }

type Post {
  id: ID!
  title: String!
  published: Boolean!
  author: Author!
}

input CreatePostInput { title: String!, published: Boolean = false }

type PostEdge { node: Post!, cursor: String! }
type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}
type PostConnection { edges: [PostEdge!]!, pageInfo: PageInfo! }

type Query {
  posts: [Post!]!
  postConnection(first: Int = 10, after: String): PostConnection!
}

type Mutation {
  createPost(input: CreatePostInput!): Post!
  updatePost(id: ID!, title: String!): Post!
  deletePost(id: ID!): ID!
}
```

## 2. 입력과 출력에 서로 다른 정책을 둔다

생성 입력에는 authorId를 받지 않는다. 현재 사용자를 쓰기 주체로 사용한다. 공개 출력에는 비밀번호나 내부 역할을 넣지 않는다. 첫 서버의 패키지 설치 위에 Prisma와 DataLoader를 추가한다. [GraphQL · Schemas and Types](https://graphql.org/learn/schema/) · [GraphQL · Authorization](https://graphql.org/learn/authorization/) · [Apollo Server · Context](https://www.apollographql.com/docs/apollo-server/data/context) · [GraphQL · DataLoader](https://github.com/graphql/dataloader/tree/v2.2.3)
