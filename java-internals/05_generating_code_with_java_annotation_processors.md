# Generating Code with Java Annotation Processors

`Main.java`가 아직 디스크에 없는 `OrderTypeName`을 참조해도 한 번의 `javac` 호출로 컴파일할 수 있다. 애너테이션 프로세서가 `@GenerateTypeName`이 붙은 `Order`를 읽고 `OrderTypeName.java`를 만들면, 컴파일러는 생성한 소스와 처음 받은 소스를 함께 컴파일한다. 이 실습은 JDK 21 이상과 `javac`를 사용한다. [javac의 애너테이션 처리](https://docs.oracle.com/en/java/javase/25/docs/specs/man/javac.html#annotation-processing)

## 1. 표준 애너테이션 프로세서가 다루는 것

JSR 269는 컴파일 중 애너테이션과 Java 선언을 읽고 처리하는 API를 정의한다. 프로세서는 `javax.lang.model`의 `TypeElement`, `VariableElement`, `TypeMirror` 등으로 선언과 타입을 조사한다. `javax.annotation.processing`의 표준 API로는 소스, 클래스, 리소스 파일을 추가하거나 애너테이션 사용 규칙을 검사할 수 있다. 원래 클래스에 멤버를 추가하는 기능은 이 API의 범위 밖에 있다. [JSR 269](https://jcp.org/en/jsr/detail?id=269) · [javac의 애너테이션 처리](https://docs.oracle.com/en/java/javase/25/docs/specs/man/javac.html#annotation-processing) · [Filer](https://docs.oracle.com/en/java/javase/25/docs/api/java.compiler/javax/annotation/processing/Filer.html)

- `RoundEnvironment`는 현재 라운드에 들어온 요소 중 특정 애너테이션이 붙은 요소를 조회한다. `processingOver()`가 `true`인 라운드에서 생성한 타입은 다음 처리 라운드의 입력이 될 수 없다. [RoundEnvironment](https://docs.oracle.com/en/java/javase/25/docs/api/java.compiler/javax/annotation/processing/RoundEnvironment.html)
- `Filer.createSourceFile()`은 생성할 타입의 정규 이름을 받는다. 생성의 근거가 된 요소도 함께 전달하면 빌드 도구가 입력과 출력의 관계를 추적하는 데 활용할 수 있다. 작성기를 닫으면 컴파일러가 그 소스를 후속 라운드에서 처리한다. 한 번의 처리 실행에서 같은 경로를 두 번 만들거나 최초 입력에 해당하는 파일을 생성하려 하면 `FilerException`이 발생한다. [Filer](https://docs.oracle.com/en/java/javase/25/docs/api/java.compiler/javax/annotation/processing/Filer.html)
- `Messager`는 컴파일 진단을 남긴다. `Diagnostic.Kind.ERROR`로 보고하면 컴파일이 실패한다. 문제가 있는 `Element`를 전달하면 컴파일러가 해당 선언의 위치를 표시하는 데 활용할 수 있다. [Messager](https://docs.oracle.com/en/java/javase/25/docs/api/java.compiler/javax/annotation/processing/Messager.html)

첫 라운드는 최초 컴파일 입력을 조사한다. 새 소스가 생기면 다음 라운드는 그 소스를 조사한다. 새 파일 생성이 멈추면 컴파일러가 마지막 라운드를 호출한다. `process()`가 반환하는 `true`는 이번 호출에 전달된 애너테이션 타입을 이 프로세서가 맡아 이후 프로세서에 넘기지 않는다는 뜻이다. 다음 라운드의 진행 여부는 생성된 파일과 처리 상태에 따라 컴파일러가 결정한다. [Processor](https://docs.oracle.com/en/java/javase/25/docs/api/java.compiler/javax/annotation/processing/Processor.html) · [javac 처리 라운드](https://docs.oracle.com/en/java/javase/25/docs/specs/man/javac.html#how-annotation-processing-works)

## 2. Lombok이 같은 클래스에 메서드를 추가하는 방식

`class Order { @lombok.Getter private long id; }`를 Lombok으로 처리해 컴파일하면 `Order.class`에 `public long getId()`가 들어간다. Lombok은 `javac`에서 애너테이션 프로세서로 시작한 뒤, `javac` 내부의 추상 구문 트리(AST)에서 `Order`에 메서드 선언을 추가한다. 컴파일러는 그 선언을 다른 메서드와 함께 바이트코드로 내보낸다. [Lombok @Getter](https://projectlombok.org/features/GetterSetter) · [Lombok 실행 경로](https://projectlombok.org/contributing/lombok-execution-path) · [Lombok의 javac Getter 구현](https://github.com/projectlombok/lombok/blob/master/src/core/lombok/javac/handlers/HandleGetter.java)

컴파일된 `Order.class`가 있는 디렉터리에서 `javap -p Order`로 메서드 목록을 확인할 수 있다. `Order.java`에 적용될 변환을 소스로 보려면 `Order.java`와 `lombok.jar`가 있는 디렉터리에서 `java -jar lombok.jar delombok -p Order.java`를 사용한다. [javap](https://docs.oracle.com/en/java/javase/25/docs/specs/man/javap.html) · [Lombok Delombok](https://projectlombok.org/features/delombok)

## 3. JDK 23부터 프로세서 실행을 명시하기

JDK 23부터 `javac`는 일반 클래스 경로에 있는 프로세서를 기본으로 찾아 실행하지 않는다. `-processor`로 실행할 프로세서 이름을 지정하거나, `--processor-path` 또는 `--processor-module-path`로 검색 경로를 설정할 수 있다. `-proc:full`은 애너테이션 처리와 컴파일을 모두 활성화하고, `-proc:only`는 애너테이션 처리까지만 수행한다. 실습은 프로세서의 위치와 이름을 모두 지정한다. [JDK 23 릴리스 노트](https://www.oracle.com/java/technologies/javase/23-relnote-issues.html) · [OpenJDK의 기본 정책 변경 안내](https://inside.java/2024/06/18/quality-heads-up/) · [javac 옵션](https://docs.oracle.com/en/java/javase/25/docs/specs/man/javac.html#standard-options)

Lombok을 사용하는 Gradle 프로젝트는 Lombok을 `compileOnly`와 `annotationProcessor`에 각각 등록한다. 앞의 구성은 소스에서 Lombok 애너테이션을 찾을 때 쓰이고, 뒤의 구성은 컴파일러가 Lombok 프로세서를 불러올 때 쓰인다. Maven에서는 `provided` 의존성과 Maven Compiler Plugin의 프로세서 경로 설정을 사용한다. [Lombok Gradle 설정](https://projectlombok.org/setup/gradle) · [Lombok Maven 설정](https://projectlombok.org/setup/maven)

## 4. `@GenerateTypeName`으로 별도 클래스 만들기

빈 실습 디렉터리에 다음 네 파일을 만든다. 프로세서는 이름이 있는 패키지에 속한 최상위 타입을 처리한다. `@GenerateTypeName`이 붙은 타입과 같은 패키지에 `<타입 이름>TypeName` 클래스를 생성하며, 이 클래스의 `value()`는 원래 타입의 정규 이름을 돌려준다.

`app/demo/GenerateTypeName.java`

```java
package demo;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@Target(ElementType.TYPE)
@Retention(RetentionPolicy.SOURCE)
public @interface GenerateTypeName {
}
```

`app/demo/Order.java`

```java
package demo;

@GenerateTypeName
public class Order {
}
```

`app/demo/Main.java`

```java
package demo;

public class Main {
    public static void main(String[] args) {
        System.out.println(OrderTypeName.value());
    }
}
```

`processor/demo/TypeNameProcessor.java`

```java
package demo;

import java.io.IOException;
import java.io.Writer;
import java.util.Set;
import javax.annotation.processing.AbstractProcessor;
import javax.annotation.processing.RoundEnvironment;
import javax.annotation.processing.SupportedAnnotationTypes;
import javax.lang.model.SourceVersion;
import javax.lang.model.element.Element;
import javax.lang.model.element.PackageElement;
import javax.lang.model.element.TypeElement;
import javax.tools.Diagnostic;

@SupportedAnnotationTypes("demo.GenerateTypeName")
public class TypeNameProcessor extends AbstractProcessor {
    @Override
    public SourceVersion getSupportedSourceVersion() {
        return SourceVersion.latestSupported();
    }

    @Override
    public boolean process(Set<? extends TypeElement> annotations,
                           RoundEnvironment roundEnv) {
        if (roundEnv.processingOver() || annotations.isEmpty()) {
            return false;
        }

        TypeElement annotation = annotations.iterator().next();
        for (Element element : roundEnv.getElementsAnnotatedWith(annotation)) {
            if (!(element.getEnclosingElement() instanceof PackageElement pkg)
                    || pkg.isUnnamed()) {
                processingEnv.getMessager().printMessage(Diagnostic.Kind.ERROR,
                        "@GenerateTypeName requires a top-level type in a named package",
                        element);
                continue;
            }

            String packageName = pkg.getQualifiedName().toString();
            String typeName = packageName + "." + element.getSimpleName();
            String generatedName = element.getSimpleName() + "TypeName";
            String source = """
                    package %s;

                    final class %s {
                        static java.lang.String value() {
                            return "%s";
                        }
                    }
                    """.formatted(packageName, generatedName, typeName);

            try (Writer writer = processingEnv.getFiler()
                    .createSourceFile(packageName + "." + generatedName, element)
                    .openWriter()) {
                writer.write(source);
            } catch (IOException ex) {
                processingEnv.getMessager().printMessage(Diagnostic.Kind.ERROR,
                        "Cannot generate " + generatedName + ": " + ex.getMessage(), element);
            }
        }
        return true;
    }
}
```

프로세서가 지원하는 애너테이션 타입은 `demo.GenerateTypeName` 하나다. 이름을 문자열로 선언하고 현재 라운드가 넘겨주는 `TypeElement`로 조회하므로, 프로세서를 먼저 컴파일할 때 `GenerateTypeName.class`가 필요하지 않다. `RetentionPolicy.SOURCE`를 사용해 표식을 소스에만 유지하며, 컴파일이 끝난 뒤 `Main`은 생성된 클래스의 메서드를 호출한다. [SupportedAnnotationTypes](https://docs.oracle.com/en/java/javase/25/docs/api/java.compiler/javax/annotation/processing/SupportedAnnotationTypes.html) · [JLS의 `@Retention`](https://docs.oracle.com/javase/specs/jls/se25/html/jls-9.html#jls-9.6.4.2)

## 5. `javac`로 컴파일하고 생성 결과 확인하기

네 파일을 저장한 디렉터리에서 실행한다. 첫 번째 `javac`는 프로세서 클래스를 만들고, 두 번째 `javac`는 그 클래스를 불러 애플리케이션 소스를 처리한다. `-s`는 생성 소스의 위치를, `-d`는 컴파일된 클래스의 위치를 지정한다. [javac 표준 옵션](https://docs.oracle.com/en/java/javase/25/docs/specs/man/javac.html#standard-options)

```sh
mkdir -p build/processor build/generated build/classes
javac -proc:none -d build/processor processor/demo/TypeNameProcessor.java
javac --processor-path build/processor -processor demo.TypeNameProcessor \
    -s build/generated -d build/classes -XprintRounds app/demo/*.java
java -cp build/classes demo.Main
```

`Main`의 표준 출력은 한 줄이다.

```text
demo.Order
```

`-XprintRounds`로 첫 라운드의 `demo.GenerateTypeName`, `demo.Main`, `demo.Order`와 두 번째 라운드의 `demo.OrderTypeName`을 확인할 수 있다. 세 번째는 마지막 라운드다. 생성 소스는 `build/generated/demo/OrderTypeName.java`에, 컴파일 결과는 `build/classes/demo/OrderTypeName.class`에 있다. [javac의 라운드 출력 옵션](https://docs.oracle.com/en/java/javase/25/docs/specs/man/javac.html#extra-options)

처리 단계를 확인하려면 새 클래스 출력 디렉터리를 지정하고 `-proc:none`으로 컴파일해 본다. 이 호출에는 처음 작성한 소스만 들어가므로 `Main`의 `OrderTypeName` 참조에서 `cannot find symbol` 오류가 난다.

```sh
mkdir -p build/no-processing
javac -proc:none -classpath build/no-processing -d build/no-processing app/demo/*.java
```
