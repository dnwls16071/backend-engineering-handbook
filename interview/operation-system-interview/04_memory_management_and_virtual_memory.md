# Memory Management and Virtual Memory

## 1. 운영체제는 메모리를 어떻게 관리하나요?

**30–60초 답변**

> 운영체제는 프로세스별 가상 주소 공간과 시스템 전체의 물리 메모리를 관리합니다. 프로세스에 코드, 힙, 스택, 매핑된 파일을 위한 주소 범위와 접근 권한을 정하고, 필요한 가상 페이지에 물리 프레임을 연결합니다. 페이지 테이블에 매핑과 권한을 기록하고 MMU가 이를 사용해 주소를 변환하고 접근 권한을 확인합니다. 물리 프레임이 부족해지면 깨끗한 파일 캐시를 비우거나, 스왑을 사용할 수 있을 때 익명 페이지를 내보내 공간을 확보합니다. 매핑이 해제되면 다른 매핑이나 사용자가 참조하지 않는 프레임을 재사용할 수 있습니다. [Linux 메모리 관리 개요](https://docs.kernel.org/admin-guide/mm/concepts.html) · [Linux 페이지 테이블 문서](https://docs.kernel.org/mm/page_tables.html)

**꼬리 질문 · 1 GiB를 할당했는데 RSS는 왜 그만큼 늘지 않나요?**

Linux에서 기본적인 익명 `mmap()`은 가상 주소 범위를 먼저 만들고, 실제 접근 시점에 필요한 페이지를 매핑할 수 있습니다. 새 매핑에 쓰면 해당 범위에 물리 페이지가 할당되면서 RAM에 상주하는 메모리 크기인 RSS가 늘어납니다. 메모리 증가 원인을 볼 때는 매핑 크기와 RSS를 함께 보고, 매핑만 늘었는지 실제 사용한 페이지도 늘었는지 확인합니다. [Linux `mmap(2)`](https://man7.org/linux/man-pages/man2/mmap.2.html) · [Linux 익명 메모리 문서](https://docs.kernel.org/admin-guide/mm/concepts.html#anonymous-memory)

## 2. 내부 단편화와 외부 단편화의 차이는 무엇인가요?

**30–60초 답변**

> 내부 단편화는 이미 할당된 블록 안에서 쓰지 못하고 남는 공간입니다. 4 KiB 페이지 두 장으로 5 KiB짜리 영역을 독립적으로 할당하면 마지막 페이지에 3 KiB가 남습니다. 외부 단편화는 할당되지 않은 공간이 여러 조각으로 흩어져 연속된 공간 요청을 만족시키기 어려운 상태입니다. 예를 들어 서로 떨어진 4 KiB 빈 공간이 두 개면, 물리적으로 연속된 8 KiB 요청을 충족할 수 없습니다. 기본 페이지 단위의 페이징은 연속된 가상 주소를 흩어진 물리 프레임에 배치할 수 있어 이 제약을 줄입니다. [OSTEP의 가용 공간과 외부 단편화](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-freespace.pdf) · [OSTEP의 페이징](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-paging.pdf)

**꼬리 질문 · 페이징을 쓰는데도 Linux에 메모리 컴팩션이 필요한 이유는 무엇인가요?**

큰 페이지처럼 연속된 물리 프레임이 필요한 요청이 있기 때문입니다. Linux의 메모리 컴팩션(compaction)은 옮길 수 있는 페이지를 이동시켜 흩어진 빈 프레임을 연속된 영역으로 모읍니다. 전체 여유 메모리가 충분해도 이동할 수 없는 페이지가 중간에 있으면 요청한 크기의 연속 영역을 확보하기 어려울 수 있습니다. [Linux 메모리 컴팩션](https://docs.kernel.org/admin-guide/mm/concepts.html#compaction) · [Linux Transparent Hugepage 문서](https://docs.kernel.org/admin-guide/mm/transhuge.html)

## 3. 가상 메모리란 무엇이며 왜 필요한가요?

**30–60초 답변**

> 가상 메모리는 프로그램이 사용하는 주소와 실제 물리 메모리의 배치를 분리하는 추상화입니다. 각 프로세스가 자기 주소 공간을 갖기 때문에 서로 같은 가상 주소를 사용해도 다른 물리 프레임으로 연결할 수 있습니다. 운영체제는 페이지별 권한을 설정해 프로세스를 격리하고, 공유 라이브러리나 공유 메모리처럼 의도적으로 같은 데이터를 쓰는 경우에는 같은 프레임으로 연결할 수 있습니다. 또한 요구 페이징을 통해 실제 접근하는 페이지에만 물리 메모리를 배정할 수 있으므로, 큰 주소 공간을 확보하면서 RAM을 효율적으로 사용할 수 있습니다. [Linux 가상 메모리 개요](https://docs.kernel.org/admin-guide/mm/concepts.html#virtual-memory-primer) · [OSTEP의 가상 페이지와 물리 프레임](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-paging.pdf)

**꼬리 질문 · 스왑을 꺼도 가상 메모리를 사용하나요?**

네. 주소 변환과 프로세스 격리, 파일 매핑은 계속 동작합니다. 스왑을 끈 상태에서도 커널은 다시 읽을 수 있는 깨끗한 파일 캐시를 회수할 수 있습니다. 스왑 유무는 메모리 압박이 생겼을 때 익명 페이지를 스왑 공간으로 내보낼 수 있는지에 영향을 줍니다. [Linux 메모리 회수 문서](https://docs.kernel.org/admin-guide/mm/concepts.html#reclaim)

## 4. 가상 주소는 어떻게 물리 주소로 변환되나요?

**30–60초 답변**

> 페이징 시스템에서는 가상 주소를 가상 페이지 번호와 페이지 안의 오프셋으로 나눕니다. MMU는 TLB에서 해당 페이지의 변환 정보를 찾고, 매핑과 접근 권한이 유효하면 물리 프레임 번호에 같은 오프셋을 붙여 물리 주소를 만듭니다. TLB에 정보가 없으면 x86-64처럼 하드웨어가 페이지 테이블을 순회하는 시스템에서는 현재 주소 공간의 페이지 테이블을 읽습니다. 유효한 매핑을 찾으면 TLB를 채우고 접근을 계속합니다. 매핑이 현재 존재하지 않거나 권한 검사를 통과하지 못하면 페이지 폴트가 발생합니다. [Linux 페이지 테이블과 MMU·TLB 설명](https://docs.kernel.org/mm/page_tables.html) · [OSTEP의 주소 변환](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-paging.pdf)

**꼬리 질문 · 4 KiB 페이지에서 주소 변환을 예로 들 수 있나요?**

가상 주소가 `0x12345`라면 하위 12비트인 `0x345`가 오프셋이고 가상 페이지 번호는 `0x12`입니다. 페이지 테이블이 이 페이지를 물리 프레임 `0xAB`에 연결하면 프레임 시작 주소 `0xAB000`에 오프셋을 더해 `0xAB345`가 됩니다. 이 매핑이 RAM의 페이지 테이블에 있고 접근 권한이 맞으면, TLB 미스가 발생해도 페이지 폴트 없이 같은 주소를 얻을 수 있습니다. [OSTEP의 페이지 번호와 오프셋](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-paging.pdf)

## 5. 페이지 폴트가 발생하면 운영체제는 어떻게 처리하나요?

**30–60초 답변**

> 페이지 폴트는 CPU가 현재 매핑으로 메모리 접근을 수행할 수 없을 때 커널로 전달하는 예외입니다. 커널은 먼저 접근 주소의 가상 메모리 영역과 접근 종류가 유효한지 확인합니다. 유효한 접근이라면 처음 쓰는 익명 페이지에 0으로 초기화된 메모리를 연결하거나, 쓰기 시 복사(COW)가 필요한 경우 페이지를 복사합니다. 파일에 매핑된 페이지나 스왑으로 내보낸 페이지가 필요하면 캐시에서 찾고, 필요할 때 저장소에서 읽습니다. 준비가 되면 페이지 테이블을 갱신하고 폴트가 난 명령을 다시 실행합니다. 허용되지 않은 사용자 메모리 접근에는 Linux에서 보통 `SIGSEGV`를 전달합니다. [Linux 페이지 폴트 처리](https://docs.kernel.org/mm/page_tables.html) · [Linux `mmap(2)`의 매핑과 접근 권한](https://man7.org/linux/man-pages/man2/mmap.2.html)

**꼬리 질문 · minor fault와 major fault는 어떻게 구분하나요?**

Linux의 `getrusage()` 기준으로 minor fault는 I/O 없이 해결한 폴트이고, major fault는 I/O가 필요했던 폴트입니다. 처음 쓰는 익명 페이지를 RAM에 만들면 보통 minor fault입니다. RAM의 캐시에 없는 실행 파일이나 매핑된 데이터 파일을 읽어도 major fault가 생길 수 있으므로, 스왑이 원인인지 보려면 major fault 증가와 별도로 스왑에서 다시 읽는 양을 확인합니다. [Linux `getrusage(2)`](https://man7.org/linux/man-pages/man2/getrusage.2.html) · [Linux `vmstat(8)`](https://man7.org/linux/man-pages/man8/vmstat.8.html)

## 6. 페이지 교체 알고리즘은 어떤 기준으로 내보낼 페이지를 고르나요?

**30–60초 답변**

> 페이지 교체는 메모리에 자리가 필요할 때 어떤 페이지를 내보낼지 정합니다. FIFO는 들어온 지 가장 오래된 페이지를, LRU는 마지막 접근이 가장 오래된 페이지를 고릅니다. Clock은 참조 비트를 확인해 최근 접근한 페이지에 한 번 더 기회를 주는 방식으로 LRU를 근사합니다. OPT는 다음 접근이 가장 늦을 페이지를 고르는 기준이며 미래 접근 순서를 알아야 하므로 비교 기준으로 씁니다. 실제 커널은 최근 접근 정보와 함께 재사용 가능성, 수정된 내용을 저장하는 비용, 페이지를 회수할 수 있는지도 고려합니다. [OSTEP의 페이지 교체 정책](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-beyondphys-policy.pdf) · [Linux Multi-Gen LRU 설계](https://docs.kernel.org/mm/multigen_lru.html)

**꼬리 질문 · 사용한 지 비슷하게 오래된 두 페이지라면 무엇을 먼저 회수하나요?**

깨끗한 파일 캐시 페이지는 원본 파일에서 다시 읽을 수 있어 저장 없이 회수할 수 있습니다. 수정된 파일 페이지는 필요할 때 원본에 반영해야 하고, 보존해야 하는 익명 페이지를 내보낼 때는 스왑 같은 저장 수단이 필요합니다. Linux의 Multi-Gen LRU는 비슷한 시기에 접근된 페이지를 세대로 묶고, 접근 이력과 회수 후 다시 접근돼 폴트가 난 비율을 사용해 후보를 평가합니다. [Linux 메모리 회수 문서](https://docs.kernel.org/admin-guide/mm/concepts.html#reclaim) · [Linux Multi-Gen LRU 설계](https://docs.kernel.org/mm/multigen_lru.html)

## 7. 스왑이 자주 일어나면 왜 성능이 저하되나요?

**30–60초 답변**

> 작업 집합은 한 작업이 최근 일정 기간 동안 참조한 페이지의 집합입니다. 실행 중인 작업들의 작업 집합을 RAM에 함께 유지할 수 없으면 커널은 곧 다시 쓸 페이지까지 내보낼 수 있습니다. 작업이 그 페이지를 다시 참조하면 폴트가 나고, 디스크 기반 스왑에서는 읽기가 끝날 때까지 기다릴 수 있습니다. 빈 프레임을 만들려고 다른 페이지를 내보낸 뒤 그 페이지를 또 읽는 일이 반복되면 스래싱이 발생합니다. 페이지 회수와 저장소 대기가 늘면서 처리량이 떨어지고 응답 지연이 커집니다. [Denning의 작업 집합 모델](https://denninginstitute.com/pjd/PUBS/WSModel_1968.pdf) · [OSTEP의 스래싱과 메모리 초과 사용](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-beyondphys-policy.pdf)

**꼬리 질문 · 스왑 사용량이 높으면 바로 스래싱으로 판단하나요?**

스왑에 오래 사용하지 않은 페이지가 남아 있을 수 있습니다. 지연이 커진 시간대의 `vmstat 1`에서 `si`와 `so`를 보고 스왑에서 읽고 스왑에 쓰는 일이 반복되는지 확인합니다. `/proc/pressure/memory`와 서비스 p99를 함께 보면 메모리 압박이 실제 대기로 이어졌는지 판단할 수 있습니다. 디스크 기반 스왑이라면 장치 지연도 비교합니다. zswap처럼 RAM에 압축해 보관하는 계층이 있으면 일부 스왑 접근에 디스크 I/O 대신 압축·해제 비용이 듭니다. [Linux `vmstat(8)`](https://man7.org/linux/man-pages/man8/vmstat.8.html) · [Linux PSI 문서](https://docs.kernel.org/accounting/psi.html) · [Linux zswap 문서](https://docs.kernel.org/admin-guide/mm/zswap.html)
