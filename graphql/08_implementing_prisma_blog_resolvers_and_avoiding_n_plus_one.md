# Implementing Prisma Blog Resolvers and Avoiding N+1

게시글을 조회한 뒤 각 작성자를 독립 쿼리로 가져오면 목록 크기에 따라 DB 호출이 늘어난다. 필드 요구가 고정이면 include, 선택에 따라 달라지면 요청별 로더를 고려한다. [Prisma ORM 6 · Relations](https://www.prisma.io/docs/orm/v6/prisma-client/queries/relation-queries) · [Prisma ORM 6 · Query Optimization](https://www.prisma.io/docs/orm/v6/prisma-client/queries/query-optimization-performance) · [GraphQL · DataLoader](https://github.com/graphql/dataloader/tree/v2.2.3)

## 1. 블로그 CRUD resolver에서 조회 범위와 쓰기 주체를 고정한다

아래를 blog-resolvers.mjs로 저장한다. 인증 컨텍스트와 DataLoader, 커서 함수는 뒤 문서에서 정의한다. 읽기는 공개 글과 현재 작성자의 글만 대상으로 한다. 수정·삭제는 소유자가 일치하는 행에만 적용하고, 없는 ID와 다른 사람의 ID는 같은 코드로 처리한다. [GraphQL · Authorization](https://graphql.org/learn/authorization/) · [Apollo Server · Context](https://www.apollographql.com/docs/apollo-server/data/context) · [Prisma ORM 6 · CRUD](https://www.prisma.io/docs/orm/v6/prisma-client/queries/crud) · [Prisma ORM 6 · Transactions](https://www.prisma.io/docs/orm/v6/prisma-client/queries/transactions)

```javascript
// blog-resolvers.mjs
import { GraphQLError } from "graphql";
import { readPostConnection } from "./post-page.mjs";

function visibleTo(viewer) {
  return viewer
    ? { OR: [{ published: true }, { authorId: viewer.id }] }
    : { published: true };
}

function requireViewer(viewer) {
  if (!viewer) throw new GraphQLError("로그인이 필요합니다.", {
    extensions: { code: "UNAUTHENTICATED" },
  });
  return viewer.id;
}

function titleOf(value) {
  const title = value.trim();
  if (!title || title.length > 100) throw new GraphQLError("제목 길이를 확인하세요.", {
    extensions: { code: "BAD_USER_INPUT" },
  });
  return title;
}

function missing() {
  return new GraphQLError("게시글을 찾을 수 없습니다.", {
    extensions: { code: "NOT_FOUND" },
  });
}

export const resolvers = {
  Query: {
    posts: (_parent, _args, { prisma, viewer }) => prisma.post.findMany({
      where: visibleTo(viewer), take: 20, orderBy: [{ createdAt: "desc" }, { id: "desc" }],
    }),
    postConnection: (_parent, args, { prisma, viewer }) =>
      readPostConnection(prisma, visibleTo(viewer), args),
  },
  Post: {
    author: (post, _args, { authorLoader }) => post.author ?? authorLoader.load(post.authorId),
  },
  Mutation: {
    createPost: (_parent, { input }, { prisma, viewer }) => {
      const authorId = requireViewer(viewer);
      return prisma.post.create({
        data: { title: titleOf(input.title), published: input.published ?? false, authorId },
      });
    },
    updatePost: (_parent, { id, title }, { prisma, viewer }) => {
      const authorId = requireViewer(viewer);
      const newTitle = titleOf(title);
      return prisma.$transaction(async tx => {
        const changed = await tx.post.updateMany({
          where: { id, authorId }, data: { title: newTitle },
        });
        if (changed.count !== 1) throw missing();
        return tx.post.findUniqueOrThrow({ where: { id } });
      });
    },
    deletePost: async (_parent, { id }, { prisma, viewer }) => {
      const authorId = requireViewer(viewer);
      const changed = await prisma.post.deleteMany({ where: { id, authorId } });
      if (changed.count !== 1) throw missing();
      return id;
    },
  },
};
```

## 2. 선조회와 배치 조회의 비용을 비교한다

읽기 경로가 작성자를 항상 필요로 한다면 findMany에 include: { author: true }를 넣고 Post.author가 읽을 값을 먼저 가져올 수 있다. include의 SQL 실행 모양은 데이터베이스와 로딩 전략에 따라 달라질 수 있다. author를 자주 생략하는 경로는 요청별 로더로 필요한 경우에만 가져오고, 두 방식 모두 쿼리 로그로 호출 수를 확인한다. [Prisma ORM 6 · Relations](https://www.prisma.io/docs/orm/v6/prisma-client/queries/relation-queries) · [Prisma ORM 6 · Query Optimization](https://www.prisma.io/docs/orm/v6/prisma-client/queries/query-optimization-performance) · [GraphQL · DataLoader](https://github.com/graphql/dataloader/tree/v2.2.3)
