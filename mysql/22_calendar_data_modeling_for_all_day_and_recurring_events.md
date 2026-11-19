# Calendar Data Modeling for All-Day and Recurring Events

캘린더는 한 번 열리는 일정, 여러 날에 걸친 종일 일정, 반복 일정과 개별 발생의 예외를 표현한다. Google Calendar API가 공개한 날짜·시각·반복 의미를 바탕으로 예제 데이터 모델을 설계한다. 실습 환경은 MySQL 8.4(InnoDB)다. [Google Calendar Concepts](https://developers.google.com/workspace/calendar/api/concepts/events-calendars) · [Google Calendar Events Resource](https://developers.google.com/workspace/calendar/api/v3/reference/events)

## 1. 논리 모델과 종일 일정

일정에는 캘린더, 일정 ID, 표시 제목, 일정 종류, 시작과 종료가 있다. 종일 일정은 날짜로 저장하고 시각 일정은 시간대가 있는 시각으로 해석한다. Google Calendar API의 `start.date`와 `end.date`는 종일 일정에 쓰이며, 종료 날짜는 포함하지 않는다. 3월 8일과 9일에 걸친 일정은 `[2025-03-08, 2025-03-10)`이다. 조회 구간과 겹치는 조건은 `start < window_end AND end > window_start`로 표현할 수 있다. [Google Calendar Events Resource](https://developers.google.com/workspace/calendar/api/v3/reference/events) · [Events List Filters](https://developers.google.com/workspace/calendar/api/v3/reference/events/list)

```sql
CREATE TABLE mysql_lab_all_day_events (
    event_id BIGINT PRIMARY KEY,
    calendar_id BIGINT NOT NULL,
    title VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date_exclusive DATE NOT NULL,
    CHECK (start_date < end_date_exclusive),
    INDEX idx_all_day_calendar_start (calendar_id, start_date)
) ENGINE = InnoDB;

INSERT INTO mysql_lab_all_day_events
VALUES (1, 10, 'Company retreat', '2025-03-08', '2025-03-10');

SELECT event_id, title
FROM mysql_lab_all_day_events
WHERE calendar_id = 10
  AND start_date < '2025-03-10'
  AND end_date_exclusive > '2025-03-09';
```

3월 9일의 조회에는 이 일정이 포함된다. 종일 일정을 시각 기반 화면과 함께 표시할 때는 화면의 날짜와 시간대 경계를 먼저 정한다.

## 2. 반복 규칙과 서로 의존하는 속성

반복 시리즈는 시작 날짜 또는 지역 시각, 지속 시간이나 종료, 반복 규칙, 시각 일정의 시간대, 개별 예외를 함께 해석한다. 예를 들어 뉴욕에서 매주 금요일 낮 12시에 시작하는 일정은 서머타임 전후에 서로 다른 UTC 시각으로 변환된다. 첫 발생의 UTC 값에 7일을 계속 더하면 지역 시각이 달라질 수 있다. [Google Calendar Recurring Events](https://developers.google.com/workspace/calendar/api/guides/recurringevents) · [RFC 5545 iCalendar](https://www.rfc-editor.org/rfc/rfc5545.html)

| 저장 단위 | 보관할 정보 |
| --- | --- |
| 반복 시리즈 | 시리즈 ID, 시작 값, 반복 규칙(`RRULE`), 시각 일정의 IANA 시간대 |
| 개별 발생의 예외 | 시리즈 ID, 원래 발생의 시작 값, 취소 여부 또는 변경된 시각·제목 |
| 표시할 슬롯 | 원래 발생의 키, 실제 시작과 종료, 캘린더 ID |

Google Calendar API에서는 변경된 발생도 `recurringEventId`와 `originalStartTime`으로 적절한 반복 시리즈와 원래 발생을 식별할 수 있다. 따라서 옮긴 뒤의 시작 값으로 원래 발생을 식별하면 예외를 덮어쓸 때 문제가 생긴다. [Google Calendar Recurring Events](https://developers.google.com/workspace/calendar/api/guides/recurringevents)

## 3. 렌더링 모델 · 조회 기간의 발생을 슬롯으로 표현

원본 규칙에서 화면에 필요한 기간만 펼치고, 취소나 이동 예외를 적용한다. 긴 범위의 반복 일정은 전체 수명에 걸쳐 저장하는 대신 일정 기간의 슬롯만 미리 계산할 수 있다. 다음 SQL은 시각 일정의 표시용 슬롯을 UTC로 저장하는 설계 예시다. 종일 슬롯은 날짜 범위로 조회한다.

```sql
CREATE TABLE mysql_lab_timed_event_slots (
    calendar_id BIGINT NOT NULL,
    series_id BIGINT NOT NULL,
    original_start_utc DATETIME NOT NULL,
    starts_at_utc DATETIME NOT NULL,
    ends_at_utc DATETIME NOT NULL,
    PRIMARY KEY (calendar_id, series_id, original_start_utc),
    CHECK (starts_at_utc < ends_at_utc),
    INDEX idx_timed_slot_calendar_start (calendar_id, starts_at_utc)
) ENGINE = InnoDB;

INSERT INTO mysql_lab_timed_event_slots VALUES
    (10, 20, '2025-03-07 17:00:00', '2025-03-07 17:00:00', '2025-03-07 18:00:00'),
    (10, 20, '2025-03-14 16:00:00', '2025-03-14 17:00:00', '2025-03-14 18:00:00');

SELECT series_id, original_start_utc, starts_at_utc, ends_at_utc
FROM mysql_lab_timed_event_slots
WHERE calendar_id = 10
  AND starts_at_utc < '2025-03-15 00:00:00'
  AND ends_at_utc > '2025-03-14 00:00:00'
ORDER BY starts_at_utc, series_id, original_start_utc;
```

두 번째 슬롯은 원래 16시 UTC인 발생이 17시 UTC로 이동한 예다. 원본 규칙이나 예외가 바뀌면 영향받은 기간의 슬롯을 다시 만든다.
