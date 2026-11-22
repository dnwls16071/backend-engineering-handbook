# Modeling GraphQL Type Relationships

GraphQL Post.author는 게시글에서 작성자를 탐색하는 공개 계약이다. DB에서는 Post.authorId가 Author.id를 참조하고, Prisma에서 관계를 선언한다. [GraphQL · Schemas and Types](https://graphql.org/learn/schema/) · [Prisma ORM 6 · Relations in Schema](https://www.prisma.io/docs/orm/v6/prisma-schema/data-model/relations)

## 1. Prisma 모델에 외래 키와 조회 순서를 정의한다

프로젝트의 prisma/schema.prisma에 아래를 저장한다. 이 예시는 Prisma 6.19.3의 prisma-client-js와 SQLite를 사용한다. Post.authorId는 관계를 보관하는 실제 값이고 author는 ORM 관계 필드다. [Prisma ORM 6 · Relations in Schema](https://www.prisma.io/docs/orm/v6/prisma-schema/data-model/relations) · [Prisma ORM 6 · SQLite](https://www.prisma.io/docs/orm/v6/overview/databases/sqlite) · [Prisma 6.19.3 · Release](https://github.com/prisma/orm/releases/tag/6.19.3)

```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "sqlite"
  url      = env("DATABASE_URL")
}

model Author {
  id    String @id @default(cuid())
  name  String
  posts Post[]
}

model Post {
  id        String   @id @default(cuid())
  title     String
  published Boolean  @default(false)
  createdAt DateTime @default(now())
  authorId  String
  author    Author   @relation(fields: [authorId], references: [id], onDelete: Restrict)

  @@index([published, createdAt, id])
  @@index([authorId, createdAt, id])
}
```

## 2. 필드 관계와 SQL 로딩 방법을 따로 선택한다

게시글에 작성자가 있어야 하는 스키마에서는 DB 관계를 필수로 둔다. GraphQL author를 선택하지 않은 응답은 작성자를 내보내지 않으며, ORM의 선조회와 요청별 배치는 쿼리 비용에 맞춰 선택한다. [GraphQL · Schemas and Types](https://graphql.org/learn/schema/) · [Prisma ORM 6 · Relations](https://www.prisma.io/docs/orm/v6/prisma-client/queries/relation-queries) · [Prisma ORM 6 · Query Optimization](https://www.prisma.io/docs/orm/v6/prisma-client/queries/query-optimization-performance) · [GraphQL · DataLoader](https://github.com/graphql/dataloader/tree/v2.2.3)
