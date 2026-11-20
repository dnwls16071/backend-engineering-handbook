# Calling External APIs with Spring AI Tool Calling

Tool Calling으로 채팅 요청을 처리하는 중 현재 날씨를 조회한다. 모델은 도구 이름과 인자를 요청하고, Spring AI는 등록된 Java 메서드를 실행한다. 실행 결과를 전달받은 모델이 답변을 작성한다.

## 1. 호출 흐름

1. 앱이 사용자 메시지와 도구의 이름·설명·입력 스키마를 모델에 보낸다.
2. 모델이 `currentWeather`와 도시를 선택하면 Spring AI가 등록된 메서드에 인자를 전달한다.
3. 메서드는 허용한 도시의 좌표를 찾아 날씨 API를 호출하고 기온과 단위를 반환한다.
4. 모델은 도구 결과를 받아 사용자 언어로 답변을 생성한다.

자동 실행 흐름에서 `ToolCallingAdvisor`가 모델과 도구 간의 반복 호출을 조정하고, `ToolCallingManager`가 도구 정의를 확인하고 요청된 실행을 처리한다. 도구는 앱 코드에서 외부 API 주소, 실행 시간 제한, 허용 인자를 정한다. [Spring AI Tool Calling](https://docs.spring.io/spring-ai/reference/2.0/api/tools.html)

## 2. 지역별 날씨 도구

[채팅 API 예제](04_building_chat_apis_with_openai_and_ollama.md)에 다음 클래스를 추가한다. 실습 API는 Open-Meteo의 현재 기온 항목을 사용한다. [Open-Meteo Forecast API](https://open-meteo.com/en/docs)

```java
package demo.ai;

import java.net.http.HttpClient;
import java.time.Duration;
import java.util.Locale;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonProperty;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

public class WeatherTools {

    private static final Map<String, Location> LOCATIONS = Map.of(
            "seoul", new Location(37.5665, 126.9780),
            "busan", new Location(35.1796, 129.0756));

    private final RestClient client;

    WeatherTools(RestClient client) {
        this.client = client;
    }

    public static WeatherTools openMeteo() {
        var httpClient = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();
        var requestFactory = new JdkClientHttpRequestFactory(httpClient);
        requestFactory.setReadTimeout(Duration.ofSeconds(5));

        return new WeatherTools(RestClient.builder()
                .requestFactory(requestFactory)
                .baseUrl("https://api.open-meteo.com")
                .build());
    }

    @Tool(name = "currentWeather", description = "Get the current temperature for Seoul or Busan")
    public Weather currentWeather(@ToolParam(description = "City name: seoul or busan") String city) {
        String key = city == null ? "" : city.strip().toLowerCase(Locale.ROOT);
        Location location = LOCATIONS.get(key);
        if (location == null) {
            throw new IllegalArgumentException("Supported cities: seoul, busan");
        }

        Forecast forecast = client.get()
                .uri(builder -> builder.path("/v1/forecast")
                        .queryParam("latitude", location.latitude())
                        .queryParam("longitude", location.longitude())
                        .queryParam("current", "temperature_2m")
                        .queryParam("temperature_unit", "celsius")
                        .build())
                .retrieve()
                .body(Forecast.class);

        if (forecast == null || forecast.current() == null || forecast.current().temperature() == null) {
            throw new IllegalStateException("Weather response has no current temperature");
        }
        return new Weather(key, forecast.current().temperature(), "celsius");
    }

    public record Weather(String city, double temperature, String unit) {}
    record Location(double latitude, double longitude) {}
    record Forecast(Current current) {}
    record Current(@JsonProperty("temperature_2m") Double temperature) {}
}
```

## 3. 도구 연결과 실행

```java
package demo.ai;

import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.client.advisor.ToolCallingAdvisor;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.model.tool.ToolCallingManager;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@Service
@Profile("tools")
class WeatherChat {

    private final ChatClient client;

    WeatherChat(ChatModel model) {
        var advisor = ToolCallingAdvisor.builder()
                .toolCallingManager(ToolCallingManager.builder().build())
                .build();
        client = ChatClient.builder(model)
                .defaultSystem("For current weather, use the provided tool. Report tool failures clearly.")
                .defaultTools(WeatherTools.openMeteo())
                .defaultAdvisors(advisor)
                .build();
    }

    String answer(String question) {
        return client.prompt().user(question).call().content();
    }
}

@RestController
@Profile("tools")
class WeatherController {

    private final WeatherChat chat;

    WeatherController(WeatherChat chat) {
        this.chat = chat;
    }

    @GetMapping("/api/tools/weather")
    Answer answer(@RequestParam("question") String question) {
        return new Answer(chat.answer(question));
    }

    record Answer(String answer) {}
}

@Configuration
@Profile("tools & tools-cli")
class WeatherCliConfiguration {

    @Bean
    ApplicationRunner askWeather(WeatherChat chat) {
        return args -> {
            var questions = args.getOptionValues("weather.question");
            if (questions == null || questions.size() != 1) {
                throw new IllegalArgumentException("Use --weather.question=<question>");
            }
            System.out.println(chat.answer(questions.get(0)));
        };
    }
}
```

```bash
# 도구 호출을 지원하는 모델을 선택한다.
export OPENAI_CHAT_MODEL=gpt-4.1-mini

./gradlew bootRun --args='--spring.profiles.active=openai,tools,tools-cli --spring.main.web-application-type=none --weather.question="서울 현재 기온을 알려줘"'

./gradlew bootRun --args='--spring.profiles.active=openai,tools'
curl -G http://localhost:8080/api/tools/weather \
  --data-urlencode 'question=부산 현재 기온을 알려줘'
```

도구 단위 테스트에서는 HTTP 응답을 고정해 좌표와 기온 변환을 검사한다. 통합 테스트에서는 모델이 도구를 호출하는지 확인하고, 지원하지 않는 도시와 타임아웃에서 응답이 어떻게 처리되는지 확인한다.
