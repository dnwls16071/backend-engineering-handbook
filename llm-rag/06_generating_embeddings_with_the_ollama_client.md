# Generating Embeddings with the Ollama Client

Ollama의 POST /api/embed은 문자열 또는 배열을 입력받아 embeddings 배열을 반환한다. 배치에서는 입력과 결과의 개수와 벡터 차원을 확인한다. [Ollama · Generate Embeddings](https://docs.ollama.com/api/embed) · [Ollama Python 0.6.3](https://github.com/ollama/ollama-python/tree/v0.6.3)

## 1. 실습용 Python 패키지를 설치한다

Python 3.12 가상환경에 아래 버전을 설치한다. 실제 임베딩 실행 전 [Ollama 준비](05_running_ollama_locally.md)에서 모델이 설치됐는지 확인한다. [PyPI · chromadb 1.5.5](https://pypi.org/project/chromadb/1.5.5/) · [Ollama Python 0.6.3](https://github.com/ollama/ollama-python/tree/v0.6.3) · [Ollama · embeddinggemma](https://ollama.com/library/embeddinggemma)

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install chromadb==1.5.5 ollama==0.6.3
```

## 2. 두 문장의 임베딩을 한 번에 받아 본다

truncate=False로 설정해 문서가 입력 한도를 넘는 경우 조용히 잘리지 않게 한다. 긴 문서는 청크로 나눈다. 동일 모델에서는 고정 차원을 기대하지만 예상 차원은 사용한 태그에서 반환값으로 확인한다. [Ollama · Generate Embeddings](https://docs.ollama.com/api/embed) · [Ollama · Embeddings](https://docs.ollama.com/capabilities/embeddings) · [Google · EmbeddingGemma Model Card](https://huggingface.co/google/embeddinggemma-300m)

```python
from ollama import Client

client = Client(host="http://127.0.0.1:11434")
texts = ["배송 주소를 바꾸려면 어떻게 하나요?", "출고 전에는 배송 주소를 수정할 수 있습니다."]
vectors = client.embed(model="embeddinggemma", input=texts, truncate=False).embeddings
assert len(vectors) == len(texts)
assert vectors[0] and len(vectors[0]) == len(vectors[1])
print(f"count={len(vectors)} dimension={len(vectors[0])}")
```
