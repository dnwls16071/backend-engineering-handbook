# Running Ollama Locally

Ollama는 로컬 모델을 관리하고 기본적으로 HTTP API를 제공한다. 이 실습은 embeddinggemma를 다운로드해 로컬 임베딩을 만든다. [Ollama · macOS](https://docs.ollama.com/macos) · [Ollama · CLI](https://docs.ollama.com/cli) · [Ollama · API Introduction](https://docs.ollama.com/api/introduction) · [Ollama · embeddinggemma](https://ollama.com/library/embeddinggemma)

## 1. 설치 후 로컬 모델과 API를 확인한다

macOS에서는 공식 설치 앱을 실행하고 CLI를 사용할 수 있는지 확인한다. 앱이 이미 서버를 실행했다면 별도 serve가 필요 없다. 서버가 없는 CLI 환경에서는 별도 셸에서 ollama serve를 실행한다. [Ollama · macOS](https://docs.ollama.com/macos) · [Ollama · CLI](https://docs.ollama.com/cli) · [Ollama · API Introduction](https://docs.ollama.com/api/introduction)

```bash
ollama pull embeddinggemma
ollama list
curl -fsS http://127.0.0.1:11434/api/tags
```

## 2. 자원과 연결 범위를 확인한다

모델 다운로드와 추론은 디스크 및 메모리를 사용한다. 모델과 사용할 API 주소를 구분해 확인하고, 로컬 서비스는 루프백 주소를 기본으로 사용한다. 외부 공개가 필요한 서비스라면 인증·접근 제한을 애플리케이션 경계에서 적용한다. [Ollama · macOS](https://docs.ollama.com/macos) · [Ollama · API Introduction](https://docs.ollama.com/api/introduction) · [OWASP · RAG Security](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html)
