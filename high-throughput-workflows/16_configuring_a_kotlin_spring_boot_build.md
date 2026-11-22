# Configuring a Kotlin Spring Boot Build

Spring Boot 애플리케이션에 Spring Kafka, JDBC, Temporal Java SDK를 연결한다. Gradle Wrapper와 JVM toolchain을 사용해 실습 환경 차이를 줄인다. [Spring Boot 3.5 · Kotlin Support](https://docs.spring.io/spring-boot/3.5/reference/features/kotlin.html) · [Spring Boot 3.5 · System Requirements](https://docs.spring.io/spring-boot/3.5/system-requirements.html) · [Kotlin · Configure a Gradle Project](https://kotlinlang.org/docs/gradle-configure-project.html)

## 1. Gradle과 Kotlin 버전을 정렬한다

Gradle 8.13 Wrapper를 준비하고 아래를 build.gradle.kts에 저장한다. Kotlin 플러그인과 의존성 버전을 맞추고 Kotlin Spring 플러그인을 적용한다. 다음 문서의 Kotlin 클래스를 모두 src/main/kotlin/workflowlab 아래에 두면 된다. [Spring Boot 3.5 · Kotlin Support](https://docs.spring.io/spring-boot/3.5/reference/features/kotlin.html) · [Spring Boot 3.5 · System Requirements](https://docs.spring.io/spring-boot/3.5/system-requirements.html) · [Kotlin · Configure a Gradle Project](https://kotlinlang.org/docs/gradle-configure-project.html)

```kotlin
// build.gradle.kts
plugins {
    id("org.springframework.boot") version "3.5.8"
    id("io.spring.dependency-management") version "1.1.7"
    kotlin("jvm") version "2.1.21"
    kotlin("plugin.spring") version "2.1.21"
}

repositories { mavenCentral() }
extra["kotlin.version"] = "2.1.21"
kotlin { jvmToolchain(21) }

dependencies {
    implementation("org.springframework.boot:spring-boot-starter")
    implementation("org.springframework.boot:spring-boot-starter-jdbc")
    implementation("org.springframework.kafka:spring-kafka")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin")
    implementation("io.temporal:temporal-sdk:1.31.0")
    runtimeOnly("com.mysql:mysql-connector-j")
}

tasks.bootJar { archiveFileName.set("workflow-app.jar") }
```

## 2. Spring Boot 진입점을 추가한다

WorkflowApp.kt를 같은 패키지에 추가한다. 앱은 HTTP 서버 없이 Kafka 리스너와 Temporal Worker를 구동하며, 주문 삽입은 뒤의 MySQL 실습에서 수행한다. [Spring Boot 3.5 · Kotlin Support](https://docs.spring.io/spring-boot/3.5/reference/features/kotlin.html) · [Spring Boot 3.5 · Application Properties](https://docs.spring.io/spring-boot/3.5/appendix/application-properties/index.html) · [Temporal SDK 1.31.0 · WorkerFactory](https://github.com/temporalio/sdk-java/blob/v1.31.0/temporal-sdk/src/main/java/io/temporal/worker/WorkerFactory.java)

```kotlin
// WorkflowApp.kt
package workflowlab

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class WorkflowApp

fun main(args: Array<String>) {
    runApplication<WorkflowApp>(*args)
}
```
