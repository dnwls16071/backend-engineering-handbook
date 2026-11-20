# Kotlin Fundamentals: Variables, Null Safety, Types, and Operators

`val`과 `var`는 재할당 가능 여부를 정하고, 타입 뒤의 `?`는 `null` 허용 여부를 정한다. 예를 들어 `var name: String`은 다른 문자열을 대입할 수 있고, `val name: String?`은 `null`을 포함한 값을 한 번만 대입할 수 있다. 각 예제는 독립된 Kotlin/JVM 파일로 실행할 수 있다.

## 1. 변수 선언과 재할당

변수는 `이름: 타입` 순서로 선언한다. `val quantity = 2`처럼 초기값으로 타입을 추론할 수 있으면 타입을 생략한다. 선언과 초기화를 분리하면 `val quantity: Int`처럼 타입을 적고, 읽기 전에 값이 대입되어야 한다. `val`이 가변 객체를 참조하면 객체의 내용은 바꿀 수 있다. Java의 `final` 지역 변수도 참조에 같은 제약을 둔다. [Kotlin · 변수 선언](https://kotlinlang.org/docs/basic-syntax.html#variables) · [Java 17 · `final` 변수](https://docs.oracle.com/javase/specs/jls/se17/html/jls-4.html#jls-4.12.4)

```kotlin
fun main() {
    val unitPrice = 1_200
    var quantity: Int = 2
    quantity += 1

    val total: Int
    total = unitPrice * quantity

    val items = mutableListOf("Notebook")
    items.add("Pen")

    check(quantity == 3)
    check(total == 3_600)
    check(items == listOf("Notebook", "Pen"))
}
```

## 2. Null 허용 타입과 안전 호출

| 표현 | 동작 |
| --- | --- |
| `String` / `String?` | `String`은 `null`을 허용하지 않는다. `String?`의 값을 쓰려면 null일 때의 동작을 정하거나 먼저 값을 확인한다. |
| `name?.length` | `name`이 있으면 길이를 읽고, `null`이면 `null`을 반환한다. 표현식의 타입은 `Int?`이다. |
| `name ?: "Guest"` | 왼쪽이 `null`일 때만 오른쪽을 평가한다. 오른쪽에 `return`이나 `throw`를 넣을 수도 있다. |
| `name!!.length` | 이름이 반드시 있다고 단언한다. 실제 값이 `null`이면 `NullPointerException`이 발생한다. |

Java에서 nullability 정보가 없는 참조는 Kotlin에서 플랫폼 타입으로 들어올 수 있다. 반환값의 null 가능성을 확인하기 어렵다면 경계에서 `String?`처럼 명시적으로 받아 처리한다. [Kotlin · Null 안전성](https://kotlinlang.org/docs/null-safety.html) · [Kotlin · Java 플랫폼 타입](https://kotlinlang.org/docs/java-interop.html#null-safety-and-platform-types)

```kotlin
fun displayName(rawName: String?): String {
    val name = rawName?.trim() ?: return "Guest"
    return if (name.isEmpty()) "Guest" else name
}

fun main() {
    check(displayName(null) == "Guest")
    check(displayName("  ") == "Guest")
    check(displayName(" Ada ") == "Ada")
}
```

## 3. 숫자 변환과 타입 검사

- `val count = 3`의 타입은 `Int`다. `Long`을 받는 곳에서는 `count.toLong()`으로 바꾼다. 리터럴은 문맥에 따라 `val count: Long = 3`으로 대입하거나 `3L`로 타입을 표현할 수 있다. JVM에서는 가능한 곳에서 기본형을 사용하며, nullable 숫자와 제네릭의 숫자는 보통 박싱된다. [Kotlin · 숫자 타입과 변환](https://kotlinlang.org/docs/numbers.html)
- `if (value is String)`으로 확인하면 값이 중간에 바뀔 수 없다고 컴파일러가 판단한 범위에서 `value`를 `String`으로 사용한다. `as?`는 변환할 수 없으면 `null`을 반환한다. `as`로 강제 변환하면 타입이 맞지 않을 때 예외가 발생할 수 있다. [Kotlin · 타입 검사와 캐스트](https://kotlinlang.org/docs/typecasts.html)

```kotlin
fun textLength(value: Any?): Int {
    if (value is String) return value.length
    return 0
}

fun main() {
    val count = 3
    val quantity: Long = count.toLong()
    val input: Any = 42
    val name: String? = input as? String

    check(quantity == 3L)
    check(name == null)
    check(textLength("Kotlin") == 6)
    check(textLength(null) == 0)
}
```

## 4. 동등성, 범위, 연산자 오버로딩

| 표현 | 동작 |
| --- | --- |
| `a == b` / `a === b` | 참조 타입의 `==`는 null을 고려해 `equals()`로 동등성을 검사한다. `===`는 두 참조가 동일한 객체를 가리키는지 검사한다. Java에서는 각각 `Objects.equals(a, b)`, `a == b`에 대응한다. |
| `1..3` / `1..<3` | `..`는 끝값을 포함하고 `..<`는 제외한다. `value in range`로 소속 여부를 확인한다. |
| `a > b` / `a + b` | 연산자 함수를 제공하는 타입에서 `>`는 `compareTo()`의 결과를 사용하고 `+`는 `plus()`를 호출한다. 사용자 정의 타입도 `operator fun plus(...)`로 덧셈을 정의할 수 있다. |

[Kotlin · 동등성](https://kotlinlang.org/docs/equality.html) · [Kotlin · 범위와 반복](https://kotlinlang.org/docs/control-flow.html#for-loops) · [Kotlin · 연산자 오버로딩](https://kotlinlang.org/docs/operator-overloading.html)

```kotlin
data class Points(val value: Int) {
    operator fun plus(other: Points): Points = Points(value + other.value)
}

fun main() {
    val total = Points(10) + Points(5)
    val expected = Points(15)

    check(total == expected)
    check(total !== expected)
    check(3 in 1..3)
    check(3 !in 1..<3)
}
```
