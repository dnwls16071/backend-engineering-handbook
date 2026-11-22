# Combining Code, Semantic, and Parent–Child Chunking

텍스트 유형별로 경계를 선택한다. 코드의 함수·클래스, 설명문의 주제 전환, 긴 절의 부모·자식 관계를 검색 단위로 적용할 수 있다. [LangChain · Code Splitters](https://docs.langchain.com/oss/python/integrations/splitters/code_splitter) · [Python 3.12 · ast](https://docs.python.org/3.12/library/ast.html) · [LangChain · SemanticChunker](https://github.com/langchain-ai/langchain-experimental/blob/main/libs/experimental/langchain_experimental/text_splitter.py) · [LangChain · ParentDocumentRetriever](https://reference.langchain.com/python/langchain-classic/retrievers/parent_document_retriever/ParentDocumentRetriever)

## 1. 세 가지 분할의 쓰임과 비용을 비교한다

| 방식 | 사용할 경계 | 확인할 비용 | 근거 |
| --- | --- | --- | --- |
| 코드 청킹 | 구문 트리의 함수·클래스와 경로·줄 번호 | 독립 청크가 필요로 하는 타입, 이름과 주석을 보존할지 | [Python 3.12 · ast](https://docs.python.org/3.12/library/ast.html) · [LangChain · Code Splitters](https://docs.langchain.com/oss/python/integrations/splitters/code_splitter) |
| 시맨틱 청킹 | 인접 문장 임베딩의 거리 변화 | 임베딩 추가 비용, 임곗값 민감도와 매우 짧은 조각 | [LangChain · SemanticChunker](https://github.com/langchain-ai/langchain-experimental/blob/main/libs/experimental/langchain_experimental/text_splitter.py) · [scikit-learn · Cosine Similarity](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html) |
| 부모·자식 청킹 | 작은 자식을 색인하고 연결된 큰 부모를 조회 | 부모의 길이·중복, 소스 권한 확인과 반환 지연 | [LangChain · ParentDocumentRetriever](https://reference.langchain.com/python/langchain-classic/retrievers/parent_document_retriever/ParentDocumentRetriever) · [OWASP · RAG Security](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html) |

## 2. 부모를 합친 뒤에도 근거 위치를 유지한다

자식 ID, 부모 ID, 원문 버전과 자식의 위치를 기록한다. 같은 부모를 여러 번 돌려주지 않고, 생성에 넣을 부분을 예산에 맞춰 제한한다. 부모 조회에서도 권한과 삭제 상태를 검사한다. [LangChain · ParentDocumentRetriever](https://reference.langchain.com/python/langchain-classic/retrievers/parent_document_retriever/ParentDocumentRetriever) · [Liu et al. · Lost in the Middle](https://arxiv.org/abs/2307.03172) · [OWASP · RAG Security](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html)
