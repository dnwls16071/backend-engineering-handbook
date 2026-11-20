# HTTP Request Data and API Design

요청을 만들 때 먼저 어떤 자원에 어떤 동작을 요청하는지 결정한다. 다음으로 조회 조건을 쿼리에 넣을지, 서버가 처리할 데이터를 요청 콘텐츠로 보낼지 정한다. 콘텐츠를 보내는 경우 `Content-Type`으로 데이터 형식을 알려 준다.

## 1. 클라이언트가 데이터를 보내는 방법

| 상황 | 요청 예 | 데이터 위치 |
| --- | --- | --- |
| 경로로 지정한 파일 조회 | `GET /assets/logo.svg` | 경로에 파일 식별자 |
| 검색·필터·정렬 | `GET /tasks?status=open&sort=dueDate` | 쿼리에 조회 조건 |
| 일반 HTML 폼 제출 | `POST /tasks` | 본문에 `application/x-www-form-urlencoded` 데이터 |
| 파일이 포함된 HTML 폼 제출 | `POST /attachments` | 본문에 `multipart/form-data`의 여러 파트 |
| JSON 기반 API 호출 | `POST /tasks` | 본문에 `application/json` 데이터 |

정적인 파일과 요청 시 생성하는 페이지 모두 `GET`으로 조회할 수 있다. 쿼리의 사용 여부는 검색 조건이나 정렬과 같이 요청 대상을 특정하는 추가 매개변수가 필요한지에 달려 있다. 폼에서 `method="get"`을 사용하면 제출한 값이 URL의 쿼리에 들어간다. 상태를 변경하는 폼에는 `POST`를 사용한다.

## 2. 폼 인코딩과 파일 업로드

기본 `POST` 폼은 텍스트 값을 `name=value&name=value` 형태로 인코딩한다. 예를 들어 제목이 `Read notes`이고 분류가 `study`라면 본문은 `title=Read+notes&category=study`가 된다. 파일과 텍스트를 같이 올리는 경우에는 폼에 `enctype="multipart/form-data"`를 사용한다. 브라우저는 각 입력을 별도 파트에 넣고, 해당 요청의 `Content-Type`에 경계 문자열을 설정한다.

```html
<form action="/attachments" method="post" enctype="multipart/form-data">
  <label>설명 <input name="description"></label>
  <label>파일 <input type="file" name="attachment"></label>
  <button type="submit">첨부</button>
</form>
```

## 3. 누가 새 자원의 URI를 정하는가

| 설계 | 요청 예 | 주소 결정 |
| --- | --- | --- |
| 컬렉션에 추가 | `POST /tasks` | 서버가 새 작업 ID를 정한다. 성공 시 `201 Created`와 `Location: /tasks/42`를 반환할 수 있다. |
| 정해진 주소에 저장 | `PUT /files/report.pdf` | 클라이언트가 대상 주소를 알고 있다. 서버는 그 URI를 생성하거나 기존 표현을 교체한다. |
| 단일 자원 조회 | `GET /tasks/42` | 이미 정해진 하나의 자원을 가리킨다. |
| 업무 동작 실행 | `POST /orders/42/cancel` | 취소 요청과 같이 별도의 업무 처리가 필요한 경우 해당 처리를 담당할 URI를 사용한다. |

`PUT`이 새 자원을 만들면 `201`, 기존 자원을 성공적으로 교체하면 `200` 또는 `204`로 응답한다. 이 구분은 저장 요청을 어떤 URI에 보내는지와 함께 읽어야 한다.

HTML 폼의 네트워크 제출에는 `GET`과 `POST`를 사용할 수 있다. 서버가 렌더링하는 폼이라면 `GET /tasks/42/edit`로 편집 화면을 열고 `POST /tasks/42/edit`로 적용할 수 있다. API 클라이언트는 동일 자원에 `PATCH /tasks/42`를 보내는 방식도 선택할 수 있다.
