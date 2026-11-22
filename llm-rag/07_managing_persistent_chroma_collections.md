# Managing Persistent Chroma Collections

PersistentClient는 지정한 디렉터리에서 컬렉션을 관리한다. 이름이 같아도 다른 디렉터리나 tenant/database에 접속하면 같은 컬렉션이 아니다. [Chroma · Clients](https://cookbook.chromadb.dev/core/clients/) · [Chroma · Manage Collections](https://docs.trychroma.com/docs/collections/manage-collections)

## 1. 실습 컬렉션을 만들고 다시 연다

다음 코드는 임시 디렉터리에서 컬렉션 생성, 조회, 설정 읽기, 메타데이터 변경과 삭제를 실습한다. 이 컬렉션은 호출자가 직접 벡터를 전달하도록 embedding_function을 비워 둔다. [Chroma · Clients](https://cookbook.chromadb.dev/core/clients/) · [Chroma · Manage Collections](https://docs.trychroma.com/docs/collections/manage-collections) · [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure)

```python
from tempfile import TemporaryDirectory
import chromadb

with TemporaryDirectory() as directory:
    client = chromadb.PersistentClient(path=directory)
    client.create_collection(
        "rag-fixture",
        embedding_function=None,
        configuration={"hnsw": {"space": "cosine"}},
        metadata={"purpose": "lab"},
    )
    reopened = chromadb.PersistentClient(path=directory)
    collection = reopened.get_collection("rag-fixture", embedding_function=None)
    assert collection.metadata == {"purpose": "lab"}
    collection.modify(metadata={"purpose": "lab", "revision": "v1"})
    assert collection.metadata["revision"] == "v1"
    reopened.delete_collection("rag-fixture")
    assert not reopened.list_collections()
```

## 2. 운영 변경 전에 설정과 영향을 확인한다

get_or_create_collection을 기존 이름으로 호출해도 새 거리 함수로 다시 색인되지 않는다. 인덱스 설정과 컬렉션 메타데이터를 구분한다. 삭제 전에는 실습용 컬렉션 이름과 데이터 경로인지 확인한다. [Chroma · Manage Collections](https://docs.trychroma.com/docs/collections/manage-collections) · [Chroma · Configure Collections](https://docs.trychroma.com/docs/collections/configure) · [Chroma 1.5.5 · HNSW Configuration](https://raw.githubusercontent.com/chroma-core/chroma/1.5.5/chromadb/api/collection_configuration.py)
