# Adapter Pattern

어댑터는 기존 객체를 호출자가 기대하는 인터페이스로 사용할 수 있게 하는 구조 패턴이다. 객체를 감싸는 구현에서는 어댑터가 호출과 데이터를 변환한 뒤 기존 객체에 위임한다. [GoF의 Adapter](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)

## 어떤 문제를 푸는가

창고 모니터링 코드에서는 섭씨 온도를 사용하고 기존 센서 API에서는 화씨를 반환한다고 하자. 호출부마다 단위를 변환하면 변환식과 반올림 기준이 흩어진다. 기존 센서를 사용하는 어댑터가 변환을 담당하고 호출부는 섭씨 기준으로 동작하게 할 수 있다.

## Java 17 예제

```java
public class AdapterExample {
    interface WarehouseThermometer {
        double celsius();
    }

    static final class LegacySensor {
        double readFahrenheit() {
            return 77.0;
        }
    }

    record CelsiusSensorAdapter(LegacySensor sensor)
            implements WarehouseThermometer {
        @Override
        public double celsius() {
            return (sensor.readFahrenheit() - 32.0) * 5.0 / 9.0;
        }
    }

    public static void main(String[] args) {
        WarehouseThermometer thermometer = new CelsiusSensorAdapter(new LegacySensor());
        double reading = thermometer.celsius();
        if (!(Math.abs(reading - 25.0) < 0.0001)) {
            throw new AssertionError(reading);
        }
        System.out.println(reading);
    }
}
```

실행 결과는 `25.0`이다. 화씨를 반환하는 센서는 그대로 두고 어댑터 경계에서 단위를 바꾼다. JDK의 `InputStreamReader`도 바이트 입력을 지정한 문자 집합으로 해석해 문자 입력으로 제공하는 사례다. [Java InputStreamReader](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/io/InputStreamReader.html)

## 적용할 때 볼 점

- 메서드 이름이나 값의 형태뿐 아니라 오류, 누락값, 정밀도도 대상 인터페이스의 계약에 맞춘다. 센서가 유효 범위를 벗어난 값을 오류 표시로 사용한다면 해당 값이 일반 온도로 바뀌지 않도록 처리한다.
- 파사드는 여러 구성 요소에 대한 사용 흐름을 단순하게 만든다. 어댑터의 핵심은 한쪽의 계약을 다른 쪽에 맞추는 변환이다. [Facade Pattern](01_facade_pattern.md)
