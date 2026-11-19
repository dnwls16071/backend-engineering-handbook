# Refining Code for Maintainability

코드를 다듬을 때는 다음 사람이 동작과 변경 범위를 쉽게 파악하도록 배치와 이름을 정리한다. 주문 상품 코드를 예로 들어 주석과 패키지가 맡는 역할을 살펴보고, 잘못된 결과를 고친 뒤 같은 결과를 더 단순한 구현으로 계산한다.

## 1. 주석에는 판단의 근거 남기기

코드가 하는 일은 이름과 타입, 작은 메서드로 표현한다. 주석에는 코드만 보고 알기 어려운 업무상 이유, 외부 계약, 환경 제약을 남긴다. 예를 들어 “첫 등장 순서를 유지한다”는 반환 계약이다. “검수 화면에서 주문서의 상품 순서와 대조한다”는 그 계약을 정한 이유다.

리뷰에서는 현재 구현과 주석이 일치하는지 확인한다. 호출자가 알아야 하는 반환 순서나 예외는 메서드 문서에 두고, 실제로 그 계약이 유지되는지는 테스트로 확인한다.

## 2. 변수와 메서드를 읽는 순서로 배치하기

- 지역 변수는 값을 판단하거나 사용하는 위치 가까이에 선언한다. 분기 내부에서만 쓸 값은 그 분기 안에 두면 영향 범위를 좁힐 수 있다.
- 클래스는 상태와 생성 과정, 대표 연산, 세부 구현을 관련된 단위로 묶는다. 공개 메서드에서 헬퍼로 내려가며 읽을 수 있게 배치하되, 팀의 기존 관례도 고려한다.
- Java에서 필드 초기화 식이나 초기화 블록을 옮길 때는 실행 순서를 확인한다. 같은 정적 초기화 과정의 필드와 블록은 원문에 나타난 순서에 따라 초기화되는 경우가 있어, 선언 위치를 바꾸는 것만으로도 동작이 달라질 수 있다. [Java 클래스 초기화 절차](https://docs.oracle.com/javase/specs/jls/se17/html/jls-12.html#jls-12.4.2) · [인스턴스 생성과 초기화](https://docs.oracle.com/javase/specs/jls/se17/html/jls-12.html#jls-12.5)

## 3. 함께 바뀌는 코드를 패키지로 묶기

주문 검수 규칙과 상품 카탈로그 등록 규칙이 따로 바뀐다면, 각 기능의 진입점과 구현을 `shop.order`, `shop.catalog`처럼 업무 기준으로 묶을 수 있다. 주문 검수에서 쓰는 상품 코드 정리도 주문 패키지 안에 두면 규칙과 호출부를 함께 찾기 쉽다.

다른 패키지에서 호출할 계약을 먼저 정하고, 패키지 내부에서만 필요한 구현에는 그에 맞는 접근 범위를 사용한다. 여러 기능이 공용 코드를 필요로 한다면 어떤 규칙을 실제로 공유하는지 확인해 이름과 위치를 정한다. 패키지를 옮길 때는 import뿐 아니라 접근 제어, 테스트, 클래스 이름을 문자열로 참조하는 설정까지 확인한다. [Java 패키지](https://docs.oracle.com/javase/specs/jls/se17/html/jls-7.html) · [객체의 책임과 의존 방향](02_object_oriented_design_and_solid_principles.md)

## 4. 실패 사례를 재현하고 수정하기

주문서에 처음 등장한 순서대로 상품 코드를 한 번씩 반환한다고 하자. 입력은 `null`이 없는 상품 코드 목록이고, 반환값은 수정 가능한 새 목록이다. 입력이 `[P-2, P-1, P-2]`라면 결과는 `[P-2, P-1]`이어야 한다.

기존 구현은 바로 앞 코드와 비교한다. 중단점에서 세 번째 항목의 `code`와 `previousCode`를 확인하면 각각 `P-2`, `P-1`이다. 앞서 `P-2`를 담았다는 정보가 비교에 쓰이지 않아 중복이 남는다. 재현 테스트를 만든 뒤, 이미 결과에 포함된 코드인지 확인하는 방식으로 고친다.

```java
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;

final class OrderProductCodes {
    static List<String> withAdjacentCheck(List<String> productCodes) {
        var result = new ArrayList<String>();
        String previousCode = null;
        for (String code : productCodes) {
            if (!code.equals(previousCode)) {
                result.add(code);
            }
            previousCode = code;
        }
        return result;
    }

    static List<String> withMembershipCheck(List<String> productCodes) {
        var result = new ArrayList<String>();
        for (String code : productCodes) {
            if (!result.contains(code)) {
                result.add(code);
            }
        }
        return result;
    }

    static List<String> firstSeenProductCodes(List<String> productCodes) {
        return new ArrayList<>(new LinkedHashSet<>(productCodes));
    }
}
```

## 5. 반환 계약을 유지하며 알고리즘 교체하기

`withMembershipCheck`는 고친 동작을 직접 표현한다. 코드가 대부분 서로 다르면 매 항목마다 누적된 목록을 검색하는 비용이 커진다. `firstSeenProductCodes`는 `LinkedHashSet`으로 중복을 제거하고 최초 삽입 순서를 보존한 뒤, 새 `ArrayList`로 변환한다. 이렇게 하면 결과의 순서와 수정 가능성을 함께 유지한다. [Java LinkedHashSet](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/LinkedHashSet.html)

버그를 고칠 때는 실패한 입력에서 결과가 요구사항에 맞게 바뀌는지 확인한다. 이어서 알고리즘을 교체할 때는 수정된 동작을 기준으로 빈 목록, 연속·비연속 중복, 최초 등장 순서, 반환 목록의 수정이 입력에 미치는 영향을 모두 확인한다. 관찰 가능한 동작을 유지하면서 구조나 구현을 개선하는 작업이 리팩터링이다. [Martin Fowler의 리팩터링 정의](https://martinfowler.com/bliki/DefinitionOfRefactoring.html) · [테스트 실패 진단과 안전한 설계 변경](../test-driven-development/04_test_failures_and_safe_design_changes.md)

## 6. IDE 기능으로 변경 범위 확인하기

IntelliJ IDEA에서는 **Rename**으로 참조되는 이름을 함께 바꾸고, **Extract Method**로 연산을 추출하며, **Move**로 클래스의 위치를 옮길 수 있다. 적용 전에 사용처와 충돌을 확인한다. 리플렉션, 설정 파일, 외부 연동의 문자열처럼 정적 참조로 찾기 어려운 사용처는 프로젝트 검색과 테스트로 확인한다. 변경 후에는 관련 테스트를 실행하고 diff에서 의도한 범위만 바뀌었는지 살펴본다. [IntelliJ IDEA 리팩터링과 변경 미리 보기](https://www.jetbrains.com/help/idea/refactoring-source-code.html)

## 7. 핵심 키워드로 코드 검토하기

| 키워드 | 리뷰 질문 |
| --- | --- |
| 주석 | 호출자가 알아야 할 계약과 그 근거가 어디에 남아 있는가? |
| 나열 순서 | 다음 동작을 찾기 쉽고 초기화 의존성이 유지되는가? |
| 패키지 | 같은 업무 규칙을 변경할 때 관련 코드를 한곳에서 찾을 수 있는가? |
| 버그 재현과 알고리즘 교체 | 수정 전 실패를 재현했고, 교체 후에는 수정된 계약을 그대로 만족하는가? |
| IDE 리팩터링 | 사용처와 변경 내용을 검토하고 관련 테스트를 실행했는가? |
