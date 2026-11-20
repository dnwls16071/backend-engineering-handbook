# File Systems and Storage I/O

## 39. 파일 시스템은 무엇이고, 파일을 어떻게 읽고 쓰나요?

**30–60초 답변**

> 파일 시스템은 데이터와 메타데이터를 파일과 디렉터리로 조직하고, 경로로 찾아 접근할 수 있게 하는 계층입니다. Linux에서는 `open()`으로 경로를 해석하고 권한을 확인한 뒤 파일 디스크립터를 얻습니다. 일반적인 버퍼드 `read()`는 페이지 캐시에 데이터가 있으면 거기에서 가져오고, 없으면 파일 시스템과 저장 장치를 거쳐 캐시를 채운 뒤 사용자 버퍼로 복사합니다. 버퍼드 `write()`는 보통 데이터를 페이지 캐시에 복사하고 수정된 페이지를 표시합니다. 커널이 이후 저장 장치에 기록하며, 쓰기 성공을 반환하는 시점과 전원 장애 이후에도 복구할 수 있게 기록되는 시점은 달라질 수 있습니다. [Linux VFS](https://docs.kernel.org/filesystems/vfs.html) · [Linux 페이지 캐시](https://docs.kernel.org/mm/page_cache.html) · [Linux `write(2)`](https://man7.org/linux/man-pages/man2/write.2.html)

**꼬리 질문 · 기존 파일을 갱신하고 전원 장애 뒤에도 새 버전을 보려면요?**

로컬 파일 시스템에서 이름을 교체하는 경우, 같은 디렉터리에 임시 파일을 만든 다음 데이터 전체를 쓰고 임시 파일을 `fsync()`합니다. 쓰기가 일부만 성공하면 반환된 바이트 수만큼 진행하고 나머지를 이어 씁니다. 이후 임시 파일을 대상 이름으로 `rename()`하고, 이름 교체를 저장 장치에 반영하기 위해 부모 디렉터리도 `fsync()`합니다. `rename()`의 이름 교체 원자성과 장애 후 내구성은 각각 확인해야 하며, 각 호출의 성공 여부와 대상 파일 시스템의 보장 범위를 확인합니다. [Linux `write(2)`](https://man7.org/linux/man-pages/man2/write.2.html) · [Linux `rename(2)`](https://man7.org/linux/man-pages/man2/rename.2.html) · [Linux `fsync(2)`](https://man7.org/linux/man-pages/man2/fsync.2.html)

## 40. 파일과 디렉터리는 파일 시스템에서 어떻게 관리되나요?

**30–60초 답변**

> Linux의 일반적인 inode 기반 파일 시스템에서 디렉터리는 이름과 파일 식별자의 대응을 저장합니다. inode는 파일 종류, 소유자, 권한, 크기 등의 메타데이터를 갖고, 파일 시스템은 이를 통해 파일 내용의 저장 위치를 찾습니다. 같은 inode를 가리키는 디렉터리 항목이 여러 개면 하드 링크입니다. 프로세스가 파일을 열면 파일 디스크립터라는 번호를 받고, 이 번호는 커널의 열린 파일 상태를 참조합니다. 읽기 위치는 보통 이 열린 파일 상태에 있습니다. [Linux VFS](https://docs.kernel.org/filesystems/vfs.html) · [Linux `open(2)`](https://man7.org/linux/man-pages/man2/open.2.html) · [Linux `inode(7)`](https://man7.org/linux/man-pages/man7/inode.7.html)

**꼬리 질문 · 열어 둔 파일을 다른 프로세스가 삭제하면 어떻게 되나요?**

`unlink()`는 해당 이름을 제거합니다. 같은 inode를 가리키는 다른 하드 링크가 있으면 그 경로로 열 수 있습니다. 마지막 이름이 제거되어도 이미 열어 둔 디스크립터로는 계속 읽거나 쓸 수 있습니다. 마지막 링크와 마지막 열린 참조가 사라지면 파일 공간이 회수될 수 있습니다. 실행 중인 프로세스가 삭제한 로그 파일을 계속 열고 있으면 이름이 보이지 않아도 사용량이 줄지 않을 수 있습니다. [Linux `unlink(2)`](https://man7.org/linux/man-pages/man2/unlink.2.html)

**꼬리 질문 · 같은 파일의 디스크립터가 두 개면 읽기 위치를 공유하나요?**

`open()`을 두 번 호출하면 각각의 열린 파일 상태를 만들므로 읽기 위치도 독립적입니다. `dup()`으로 기존 디스크립터를 복제하면 같은 열린 파일 상태를 가리키므로 한쪽에서 읽은 만큼 다른 쪽의 읽기 위치도 전진합니다. [Linux `open(2)`](https://man7.org/linux/man-pages/man2/open.2.html) · [Linux `dup(2)`](https://man7.org/linux/man-pages/man2/dup.2.html)

## 41. 디스크 I/O가 메모리 접근보다 느린 이유는 무엇인가요?

**30–60초 답변**

> 일반 메모리 접근은 CPU가 캐시나 메모리 컨트롤러를 통해 데이터를 가져옵니다. 캐시에 없는 파일 데이터를 저장 장치에서 읽으려면 커널이 요청을 제출하고, 장치가 대기열에 있는 요청을 처리한 뒤 데이터를 전송해야 합니다. HDD는 헤드 이동과 플래터 회전 대기가 추가됩니다. SSD는 기계적 이동이 없지만 NAND 접근, 컨트롤러 처리, 대기열의 비용이 있고, 쓰기 지연은 가비지 컬렉션의 영향도 받습니다. 같은 파일을 반복해서 읽으면 페이지 캐시가 요청을 흡수할 수 있어 실제 저장 장치에 접근할 때와 지연이 다릅니다. [Linux 페이지 캐시](https://docs.kernel.org/mm/page_cache.html) · [HDD 탐색 및 회전 지연 연구](https://www.usenix.org/legacy/events/osdi08/tech/full_papers/anand/anand_html/node6.html) · [NAND 저장 장치 동작 연구](https://www.usenix.org/legacy/event/fast10/tech/full_papers/boboila.pdf)

**꼬리 질문 · 두 스토리지의 I/O 성능은 어떤 조건에서 비교하나요?**

읽기와 쓰기 비율, 순차·랜덤 접근, 블록 크기, 동시 요청 수, 캐시 상태, 쓰기 동기화 조건을 맞춥니다. 큰 순차 읽기에서는 전송률을, 작은 랜덤 요청에서는 초당 I/O 횟수와 p95·p99 지연을 함께 봅니다. 반복해서 같은 파일을 버퍼드 방식으로 읽은 값에는 페이지 캐시의 효과가 들어갑니다. 애플리케이션의 반복 조회를 평가하는지, 장치 자체를 평가하는지에 따라 측정 조건을 정합니다. [Linux 페이지 캐시](https://docs.kernel.org/mm/page_cache.html) · [디스크 I/O 접근 패턴 연구](https://www.usenix.org/legacy/event/fast05/tech/full_papers/schlosser/schlosser_html/)
