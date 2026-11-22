# Migrating a Blog Database with Prisma

Prisma Migrate는 스키마 변경을 이력으로 남기고 로컬 DB에 적용한다. Studio는 실습 DB의 데이터를 눈으로 확인하는 GUI다. [Prisma ORM 6 · Migrate Workflows](https://www.prisma.io/docs/orm/v6/prisma-migrate/workflows/development-and-production) · [Prisma · Studio](https://www.prisma.io/studio) · [Prisma ORM 6 · SQLite](https://www.prisma.io/docs/orm/v6/overview/databases/sqlite)

## 1. 개발용 DB에 마이그레이션을 적용한다

[스키마 파일](06_modeling_graphql_type_relationships.md)을 작성한 뒤 프로젝트 루트에서 실행한다. Prisma 6의 SQLite 파일 상대 경로는 스키마 위치를 기준으로 해석한다. 작성자와 게시글 테스트 데이터는 같은 SQLite DB에 넣는다. [Prisma ORM 6 · SQLite](https://www.prisma.io/docs/orm/v6/overview/databases/sqlite) · [Prisma ORM 6 · Migrate Workflows](https://www.prisma.io/docs/orm/v6/prisma-migrate/workflows/development-and-production) · [Prisma 6.19.3 · Release](https://github.com/prisma/orm/releases/tag/6.19.3)

```bash
npm install --save-exact @prisma/client@6.19.3 dataloader@2.2.3
npm install --save-dev --save-exact prisma@6.19.3
export DATABASE_URL='file:./dev.db'
npx prisma migrate dev --name init
npx prisma generate
npx prisma studio
```

## 2. 개발 명령과 배포 명령의 책임을 구별한다

migrate dev는 개발에서 마이그레이션을 만들고 적용하는 명령이다. 검토한 마이그레이션 이력을 배포할 때는 migrate deploy를 사용한다. Studio에서 직접 변경한 실습 데이터와 스키마 이력은 따로 추적한다. [Prisma ORM 6 · Migrate Workflows](https://www.prisma.io/docs/orm/v6/prisma-migrate/workflows/development-and-production) · [Prisma · Studio](https://www.prisma.io/studio)

## 3. 로컬 조회용 데이터를 넣는다

Studio 또는 Prisma Client에서 Author를 먼저 만들고 해당 ID를 사용해 Post를 추가한다. 비회원 요청에서 목록을 확인하려면 예제 Post의 published를 true로 둔다. [Prisma · Studio](https://www.prisma.io/studio) · [Prisma ORM 6 · CRUD](https://www.prisma.io/docs/orm/v6/prisma-client/queries/crud) · [GraphQL · Authorization](https://graphql.org/learn/authorization/)
