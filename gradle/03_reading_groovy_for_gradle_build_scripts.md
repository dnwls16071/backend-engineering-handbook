# Gradle 빌드 스크립트를 읽는 Groovy 기초

## 1. 독립 Groovy 스크립트 실행하기

독립적인 Groovy 스크립트를 실행하려면 호환 JDK와 Groovy를 설치한 뒤 `groovy Hello.groovy`를 사용한다. `groovy --version`으로 선택된 런타임을 확인한다. Gradle의 Groovy DSL은 Gradle 배포판에 포함된 Groovy로 실행되므로, `build.gradle`을 사용하기 위해 별도의 Groovy CLI를 설치할 필요는 없다. [Apache Groovy · Install Groovy](https://groovy-lang.org/install.html) · [Gradle · Compatibility Matrix](https://docs.gradle.org/current/userguide/compatibility.html) · [Gradle · Writing Build Scripts](https://docs.gradle.org/current/userguide/writing_build_scripts.html)

```groovy
println 'Hello, Groovy'
```

## 2. 변수, 문자열, 리스트와 맵

`def`로 변수를 선언하거나 `int`, `String`처럼 타입을 명시한다. 작은따옴표 문자열은 치환을 하지 않으며, 큰따옴표 문자열에서 보간을 사용하면 `GString`이 될 수 있다. 리스트는 `['compile', 'test']`, 맵은 `[name: 'api', port: 8080]`처럼 쓴다. 키가 `String`인 맵에 보간한 문자열을 키로 넣을 때는 `toString()`으로 타입을 맞추면 조회 불일치를 피할 수 있다. [Groovy 4.0.33 · Syntax](https://docs.groovy-lang.org/4.0.33/html/documentation/core-syntax.html) · [Groovy 4.0.33 · Semantics](https://docs.groovy-lang.org/4.0.33/html/documentation/core-semantics.html)

```groovy
def app = 'catalog'
int port = 8080
def phases = ['compile', 'test']
def options = [name: app, port: port]

println "${options.name}:${options.port}"
println phases[0]
```

## 3. 메서드, 클래스, 조건과 반복

타입을 명시하거나 `def`로 메서드를 작성할 수 있다. Groovy에서는 블록의 마지막 표현식이 반환값이 될 수 있다. 클래스에서 직접 접근 제어자를 붙이지 않은 필드는 프로퍼티가 되어 접근 메서드가 생성될 수 있다. 조건식에는 Groovy Truth가 적용되므로 빈 리스트는 거짓, 요소가 있는 리스트는 참이다. `for (item in items)`로 요소를 순회하거나 `each`에 클로저를 전달할 수 있다. [Groovy 4 · Object Orientation](https://docs.groovy-lang.org/docs/groovy-4.0.24/html/documentation/core-object-orientation.html) · [Groovy 4.0.33 · Semantics](https://docs.groovy-lang.org/4.0.33/html/documentation/core-semantics.html) · [Apache Groovy · Closures](https://docs.groovy-lang.org/latest/html/documentation/core-closures.html)

```groovy
class BuildLabel {
    String prefix

    String forTask(String task) {
        "${prefix}:${task}"
    }
}

def tasks = ['compileJava', 'test']
def label = new BuildLabel(prefix: 'app')

if (tasks) {
    for (task in tasks) {
        println label.forTask(task)
    }
}
```

## 4. 클로저와 Gradle DSL 연결하기

`repositories { mavenCentral() }`에서 중괄호는 Groovy 클로저다. Gradle은 이 설정 클로저를 통해 저장소 구성 모델을 설정하며, `dependencies`나 `tasks.register`의 설정 블록도 해당 대상의 모델을 다룬다. DSL을 읽을 때는 메서드와 클로저가 어느 Gradle 객체를 설정하는지 확인한다. [Apache Groovy · Closures](https://docs.groovy-lang.org/latest/html/documentation/core-closures.html) · [Gradle · Writing Build Scripts](https://docs.gradle.org/current/userguide/writing_build_scripts.html) · [Gradle · Declaring Dependencies](https://docs.gradle.org/current/userguide/declaring_dependencies.html)
