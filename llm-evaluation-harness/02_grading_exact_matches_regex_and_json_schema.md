# Grading Exact Matches, Regex, and JSON Schema

생성 결과의 확정 가능한 조건은 코드로 확인한다. 정확 일치, 정규식 패턴, JSON Schema는 서로 다른 실패를 잡는다. [Python 3.12 · re](https://docs.python.org/3.12/library/re.html) · [Python 3.12 · json](https://docs.python.org/3.12/library/json.html) · [JSON Schema 2020-12 · Validation](https://json-schema.org/draft/2020-12/json-schema-validation)

## 1. 검사 범위를 선택한다

| 방법 | 어떤 조건을 확인하는가 | 근거 |
| --- | --- | --- |
| 정확 일치 | 출처 ID 같은 고정값. 공백 정규화나 대소문자 처리는 업무 계약에서 정한 범위로 제한한다. | [Python 3.12 · re](https://docs.python.org/3.12/library/re.html) · [scikit-learn · Metrics and Scoring](https://scikit-learn.org/stable/modules/model_evaluation.html) |
| 정규식 | 전체 문자열 일치에는 fullmatch를 사용한다. 본문 안에서 패턴을 찾으려면 search를 사용한다. | [Python 3.12 · re](https://docs.python.org/3.12/library/re.html) |
| JSON Schema | 파싱된 값의 최상위 타입, 필수 필드, 열거값, 추가 필드 허용 여부를 확인한다. | [JSON Schema 2020-12 · Validation](https://json-schema.org/draft/2020-12/json-schema-validation) · [python-jsonschema 4.25.1 · Validation](https://python-jsonschema.readthedocs.io/en/v4.25.1/validate/) |

## 2. 파싱 실패와 스키마 실패를 구분한다

Python 3.12에서 jsonschema 4.25.1을 설치한 뒤 아래 코드를 실행한다. Python JSON 로더가 기본 허용하는 비표준 상수와 중복 키도 입력에서 거부한다. 애플리케이션에서 포맷 강제가 필요하면 검사기와 포맷 지원을 별도로 명시한다. [Python 3.12 · json](https://docs.python.org/3.12/library/json.html) · [JSON Schema 2020-12 · Validation](https://json-schema.org/draft/2020-12/json-schema-validation) · [python-jsonschema 4.25.1 · Validation](https://python-jsonschema.readthedocs.io/en/v4.25.1/validate/)

```python
import json
from jsonschema import Draft202012Validator

schema = {
    "type": "object",
    "required": ["decision", "source_id"],
    "additionalProperties": False,
    "properties": {
        "decision": {"enum": ["answer", "abstain"]},
        "source_id": {"type": ["string", "null"]},
    },
    "if": {"properties": {"decision": {"const": "answer"}}},
    "then": {"properties": {"source_id": {"type": "string", "minLength": 1}}},
    "else": {"properties": {"source_id": {"type": "null"}}},
}
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema)

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result

def reject_constant(value):
    raise ValueError(f"non-JSON constant: {value}")

def grade(raw):
    try:
        data = json.loads(
            raw, object_pairs_hook=unique_object, parse_constant=reject_constant
        )
    except ValueError:
        return "parse_error"
    if not validator.is_valid(data):
        return "schema_error"
    return "valid"

assert grade('{"decision":"answer","source_id":"OPS-1"}') == "valid"
assert grade('{"decision":"abstain","source_id":null}') == "valid"
assert grade('{"decision":"answer","source_id":null}') == "schema_error"
assert grade('{"decision":"answer","source_id":"OPS-1","extra":true}') == "schema_error"
assert grade('{"decision":"answer","source_id":NaN}') == "parse_error"
assert grade('{"decision":"answer","decision":"abstain","source_id":null}') == "parse_error"
```

## 3. 유효한 형태를 통과한 다음 사실을 검사한다

OPS-1은 형태만 충족할 수 있다. 실제 출처 집합에 존재하는지, 인용이 주장을 뒷받침하는지는 다음 채점기로 확인한다. [JSON Schema 2020-12 · Validation](https://json-schema.org/draft/2020-12/json-schema-validation) · [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [NIST · TREC Overview](https://trec.nist.gov/overview.html)
