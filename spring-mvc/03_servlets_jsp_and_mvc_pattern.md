# Servlets, JSP, and the MVC Pattern

## 1. 요청 처리와 화면 렌더링 분리하기

서블릿에서 HTML을 직접 작성하면 화면 마크업이 요청 처리 코드와 같은 클래스에 놓인다. JSP에 요청 처리와 데이터 저장까지 넣으면 화면 변경 시 업무 흐름도 함께 살펴봐야 한다. MVC에서는 컨트롤러, 모델, 뷰가 각각 맡을 일을 정한다. [Jakarta Servlet 6.0 · 요청 전달](https://jakarta.ee/specifications/servlet/6.0/jakarta-servlet-spec-6.0) · [Jakarta Pages 3.1](https://jakarta.ee/specifications/pages/3.1/)

| 역할 | 메모 화면에서 하는 일 |
| --- | --- |
| 컨트롤러 | 요청 파라미터를 읽고 저장이나 조회를 호출한 뒤 보여 줄 화면을 결정한다. |
| 모델 | 메모 목록이나 폼 오류처럼 화면에 필요한 데이터를 전달한다. |
| 뷰 | JSP가 모델을 읽어 HTML을 렌더링한다. |

## 2. 컨트롤러에서 JSP로 모델 전달하기

메모 목록을 요청 속성에 저장한 뒤 `RequestDispatcher.forward()`로 JSP를 호출한다. 포워드는 서버 내부에서 같은 요청을 넘기므로 JSP가 `notes` 속성을 읽을 수 있다. `/WEB-INF/views/` 아래에 둔 JSP는 내부 포워드로 접근한다. [Jakarta Servlet 6.0 · 요청 전달과 WEB-INF](https://jakarta.ee/specifications/servlet/6.0/jakarta-servlet-spec-6.0)

```java
request.setAttribute("notes", List.of("Read HTTP", "Review MVC"));
request.getRequestDispatcher("/WEB-INF/views/notes.jsp").forward(request, response);
```

Jakarta Pages와 Jakarta Tags를 사용하는 환경에서는 EL로 모델에 접근하고 `c:forEach`로 목록을 반복한다. 제목을 HTML 텍스트 위치에 표시할 때 `c:out`으로 이스케이프한다. [Jakarta Pages 3.1](https://jakarta.ee/specifications/pages/3.1/) · [Jakarta Tags 3.0](https://jakarta.ee/specifications/tags/3.0/)

```jsp
<%@ page contentType="text/html;charset=UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<ul>
  <c:forEach var="title" items="${notes}">
    <li><c:out value="${title}" /></li>
  </c:forEach>
</ul>
```

## 3. 저장 후 목록으로 이동하기

입력 검증에 실패했다면 폼 값과 오류를 요청 속성에 담아 폼 JSP로 포워드할 수 있다. 저장에 성공했다면 `303 See Other`와 목록 URL을 담은 `Location` 헤더를 보내 브라우저가 목록에 새 GET 요청을 하도록 한다. 이렇게 구성하면 저장 뒤 새로고침할 때 목록을 다시 조회한다. 목록 요청의 모델은 GET 컨트롤러가 새로 채운다. [RFC 9110 · 303 See Other](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.4.4)

요청 경로 매핑과 뷰 호출 코드가 컨트롤러마다 반복되면 [프런트 컨트롤러](04_building_a_front_controller_framework.md)로 모을 수 있다.
