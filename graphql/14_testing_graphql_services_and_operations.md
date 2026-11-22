# Testing GraphQL Services and Operations

단위 테스트는 배치·인가 같은 서비스 동작을, GraphQL 연산 테스트는 SDL·검증·resolver 연결과 응답 모양을 확인한다. HTTP·WebSocket 계층은 실제 전송을 포함한 검사를 별도로 둔다. [Node.js 24 · Test Runner](https://nodejs.org/download/release/v24.5.0/docs/api/test.html) · [Apollo Server · Integration Testing](https://www.apollographql.com/docs/apollo-server/testing/testing) · [Apollo Server · Subscriptions](https://www.apollographql.com/docs/apollo-server/data/subscriptions)

## 1. Node 테스트 러너와 격리된 Prisma DB를 사용한다

다음 코드를 blog.test.mjs로 저장한다. 별도의 DATABASE_URL=file:./test.db에 migrate deploy와 generate를 실행한 뒤 node --test blog.test.mjs로 실행한다. 단위 테스트는 작성자 순서를, 연산 테스트는 공개 글·본인 글·인가 오류·같은 시각의 커서 경계를 검증한다. [Node.js 24 · Test Runner](https://nodejs.org/download/release/v24.5.0/docs/api/test.html) · [Prisma ORM 6 · Migrate Workflows](https://www.prisma.io/docs/orm/v6/prisma-migrate/workflows/development-and-production) · [Apollo Server · Integration Testing](https://www.apollographql.com/docs/apollo-server/testing/testing) · [GraphQL · DataLoader](https://github.com/graphql/dataloader/tree/v2.2.3) · [Relay · GraphQL Cursor Connections](https://relay.dev/graphql/connections.htm)

```javascript
// blog.test.mjs
import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { ApolloServer } from "@apollo/server";
import { PrismaClient } from "@prisma/client";
import { createAuthorLoader } from "./author-loader.mjs";
import { requestContext } from "./blog-context.mjs";
import { resolvers } from "./blog-resolvers.mjs";
import { formatBlogError } from "./blog-errors.mjs";

test("author loader batches keys and preserves caller order", async () => {
  let calls = 0;
  const loader = createAuthorLoader({ author: {
    async findMany() {
      calls++;
      return [{ id: "a", name: "A" }, { id: "b", name: "B" }];
    },
  } });
  const result = await Promise.all(["b", "a", "b"].map(id => loader.load(id)));
  assert.deepEqual(result.map(author => author.id), ["b", "a", "b"]);
  assert.equal(calls, 1);
});

test("blog operations preserve authorization and cursor order", async () => {
  const prisma = new PrismaClient();
  const server = new ApolloServer({
    typeDefs: readFileSync(new URL("./blog.graphql", import.meta.url), "utf8"),
    resolvers,
    formatError: formatBlogError,
  });
  const authors = [];
  const run = async (query, variables, viewer = null) => {
    const response = await server.executeOperation(
      { query, variables }, { contextValue: requestContext(prisma, viewer) },
    );
    assert.equal(response.body.kind, "single");
    return response.body.singleResult;
  };

  try {
    const alice = await prisma.author.create({ data: { name: "Alice" } });
    authors.push(alice.id);
    const bob = await prisma.author.create({ data: { name: "Bob" } });
    authors.push(bob.id);
    const createdAt = new Date("2026-11-01T12:00:00.000Z");
    const publicRows = await Promise.all(["A", "B"].map(title => prisma.post.create({
      data: { title, published: true, authorId: alice.id, createdAt },
    })));
    const draft = await prisma.post.create({
      data: { title: "Draft", authorId: bob.id, createdAt },
    });

    const listing = "{ posts { id title author { name } } }";
    const published = await run(listing);
    assert.equal(published.errors, undefined);
    assert.deepEqual(published.data.posts.map(post => post.id).sort(),
      publicRows.map(post => post.id).sort());
    assert.equal(published.data.posts[0].author.name, "Alice");
    const ownerView = await run(listing, {}, { id: bob.id });
    assert.ok(ownerView.data.posts.some(post => post.id === draft.id));

    const update = 'mutation Update($id: ID!) { updatePost(id: $id, title: "changed") { title } }';
    const anonymous = await run(update, { id: draft.id });
    assert.equal(anonymous.errors[0].extensions.code, "UNAUTHENTICATED");
    const denied = await run(update, { id: draft.id }, { id: alice.id });
    assert.equal(denied.errors[0].extensions.code, "NOT_FOUND");
    const allowed = await run(update, { id: draft.id }, { id: bob.id });
    assert.equal(allowed.data.updatePost.title, "changed");

    const page = `query Page($cursor: String) {
      postConnection(first: 1, after: $cursor) {
        edges { node { id } }
        pageInfo { endCursor hasNextPage }
      }
    }`;
    const first = (await run(page)).data.postConnection;
    const second = (await run(page, { cursor: first.pageInfo.endCursor })).data.postConnection;
    assert.equal(first.pageInfo.hasNextPage, true);
    assert.equal(second.pageInfo.hasNextPage, false);
    assert.notEqual(first.edges[0].node.id, second.edges[0].node.id);
  } finally {
    try {
      await server.stop();
      await prisma.post.deleteMany({ where: { authorId: { in: authors } } });
      await prisma.author.deleteMany({ where: { id: { in: authors } } });
    } finally {
      await prisma.$disconnect();
    }
  }
});
```

## 2. HTTP와 구독의 수명도 별도로 검증한다

executeOperation에 contextValue를 주입하면 HTTP 컨텍스트 함수는 거치지 않는다. 토큰 헤더를 처리하는 HTTP 테스트와, 실제 WebSocket에서 연결·구독·이벤트·종료를 확인하는 테스트를 별도로 둔다. [Apollo Server · Integration Testing](https://www.apollographql.com/docs/apollo-server/testing/testing) · [Apollo Server · Context](https://www.apollographql.com/docs/apollo-server/data/context) · [graphql-ws · Protocol](https://github.com/enisdenjo/graphql-ws/blob/master/PROTOCOL.md) · [Apollo Server · Subscriptions](https://www.apollographql.com/docs/apollo-server/data/subscriptions)
