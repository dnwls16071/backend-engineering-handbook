# Getting Started with JPA

JPA는 자바 객체와 관계형 데이터베이스를 연결하는 API다. 애플리케이션은 엔티티를 저장하거나 조회하고, Hibernate 같은 구현체가 매핑과 SQL 실행을 담당한다. 예제는 **Java 17, Jakarta Persistence 3.1, Hibernate ORM 6.6, H2**를 기준으로 한다.

## 1. 엔티티 선언과 영속성 유닛

```java
package example.jpa;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "workspaces")
public class Workspace {
    @Id
    @GeneratedValue
    private Long id;

    private String name;

    protected Workspace() {}

    public Workspace(String name) {
        this.name = name;
    }

    public void rename(String name) {
        this.name = name;
    }
}
```

`@Entity`는 JPA가 관리할 클래스, `@Id`는 기본 키, `@Table`은 매핑할 테이블을 지정한다. `org.hibernate.orm:hibernate-core`와 `com.h2database:h2`를 사용하는 일반 Java 프로젝트의 `src/main/resources/META-INF/persistence.xml`에 아래 영속성 유닛을 둔다. 다음 예제의 엔티티를 같은 영속성 유닛에 추가할 때는 해당 클래스를 `<class>`로 등록할 수 있다. [Jakarta Persistence 3.1 · persistence.xml](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1#persistence-xml-file)

```xml
<persistence xmlns="https://jakarta.ee/xml/ns/persistence" version="3.0">
    <persistence-unit name="workspace-demo" transaction-type="RESOURCE_LOCAL">
        <class>example.jpa.Workspace</class>
        <properties>
            <property name="jakarta.persistence.jdbc.driver" value="org.h2.Driver"/>
            <property name="jakarta.persistence.jdbc.url"
                      value="jdbc:h2:mem:workspace;DB_CLOSE_DELAY=-1"/>
            <property name="jakarta.persistence.jdbc.user" value="sa"/>
            <property name="jakarta.persistence.schema-generation.database.action"
                      value="drop-and-create"/>
        </properties>
    </persistence-unit>
</persistence>
```

`drop-and-create`는 메모리 예제에서 실행할 때마다 스키마를 새로 만든다. Hibernate는 JDBC 연결 정보로 DB 방언을 선택하고, 방언에 따라 페이징이나 식별자 생성에 필요한 SQL을 구성한다. [Jakarta Persistence 3.1 · 스키마 생성](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1#a12917)

## 2. EntityManager와 트랜잭션

```java
package example.jpa;

import jakarta.persistence.EntityManager;
import jakarta.persistence.EntityManagerFactory;
import jakarta.persistence.EntityTransaction;
import jakarta.persistence.Persistence;

public class JpaDemo {
    public static void main(String[] args) {
        EntityManagerFactory factory =
            Persistence.createEntityManagerFactory("workspace-demo");
        try {
            EntityManager em = factory.createEntityManager();
            EntityTransaction tx = em.getTransaction();
            try {
                tx.begin();
                em.persist(new Workspace("Platform"));
                tx.commit();
            } catch (RuntimeException e) {
                if (tx.isActive()) {
                    tx.rollback();
                }
                throw e;
            } finally {
                em.close();
            }
        } finally {
            factory.close();
        }
    }
}
```

`EntityManagerFactory`는 영속성 유닛마다 초기화해 여러 작업에서 재사용한다. `EntityManager`는 작업 범위마다 만들고 스레드 사이에 공유하지 않는다. 저장, 수정, 삭제는 트랜잭션 안에서 수행한다. [Jakarta Persistence 3.1 · EntityManager 관리](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1#a11431) · [Jakarta Persistence 3.1 · 리소스 로컬 트랜잭션](https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1#resource-local-entitymanagers)

## 3. 기본 키 조회와 JPQL

기본 키를 알고 있다면 `em.find(Workspace.class, id)`를 사용한다. 이름처럼 기본 키 이외의 조건으로 여러 엔티티를 찾을 때는 JPQL을 사용한다.

```java
List<Workspace> matches = em.createQuery(
        "select w from Workspace w where w.name = :name order by w.id",
        Workspace.class)
    .setParameter("name", "Platform")
    .setMaxResults(20)
    .getResultList();
```

JPQL의 `Workspace`와 `name`은 엔티티 이름과 자바 속성이다. 트랜잭션 안에서 저장한 객체가 관리되는 과정은 [02번 문서](02_jpa_persistence_context_and_entity_lifecycle.md)에서 이어진다.
