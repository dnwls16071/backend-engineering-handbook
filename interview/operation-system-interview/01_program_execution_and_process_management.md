# Program Execution and Process Management

## 3. 운영체제 관점에서 프로그램의 실행 과정을 설명해 주세요.

**30–60초 답변**

> Linux 셸에서 외부 명령을 실행하는 경우, 흔히 셸이 `fork()`로 자식 프로세스를 만들고 자식이 `execve()`로 실행을 요청합니다. `execve()`가 성공하면 PID를 유지한 채 실행 이미지가 바뀝니다. 커널은 ELF 실행 파일에서 로드할 영역을 새 가상 주소 공간에 매핑하고, 초기 스택에 명령행 인자와 환경 변수를 준비합니다. 동적 링크 실행 파일이면 사용자 모드 실행은 동적 링커에서 시작하고, 필요한 라이브러리가 준비되면 프로그램의 시작 코드로 이어집니다. C 프로그램에서는 시작 코드가 런타임을 초기화하고 `main()`을 호출합니다. [Linux `fork(2)`](https://man7.org/linux/man-pages/man2/fork.2.html) · [Linux `execve(2)`](https://man7.org/linux/man-pages/man2/execve.2.html) · [Linux ELF 로더](https://github.com/torvalds/linux/blob/master/fs/binfmt_elf.c) · [glibc 시작 코드](https://github.com/bminor/glibc/blob/master/csu/libc-start.c)

**꼬리 질문 · 실행 파일 전체가 RAM에 올라와야 실행할 수 있나요?**

가상 주소 공간에 실행 파일의 영역이 매핑되면 필요한 페이지를 실제 접근 시점에 가져올 수 있습니다. 아직 접근할 수 있는 페이지가 준비되지 않았다면 페이지 폴트가 발생하고, 커널은 유효한 매핑인지 확인해 페이지를 연결한 뒤 해당 명령을 다시 실행하게 합니다. 이미 페이지 캐시에 있는 파일 페이지는 다시 디스크에서 읽을 필요 없이 연결할 수 있습니다. [Linux 커널의 가상 메모리와 페이지 캐시](https://docs.kernel.org/admin-guide/mm/concepts.html)

## 4. 프로세스의 상태와 상태 전이를 설명해 주세요.

**30–60초 답변**

> 기본 모델에서는 생성, 준비, 실행, 대기, 종료 상태를 구분합니다. 생성된 실행 단위는 준비 상태에서 CPU를 기다리고, 스케줄러가 선택하면 실행 상태가 됩니다. 실행 중 선점되면 준비 상태로 돌아갑니다. 읽을 데이터가 없는 블로킹 I/O처럼 기다려야 할 조건이 생기면 대기 상태로 들어갑니다. I/O가 완료되면 다시 준비 상태가 되고, CPU에 배정될 때 실행을 이어갑니다. Linux에서 CPU를 배정하는 대상은 스레드 단위이므로 한 프로세스에서도 스레드마다 상태가 다를 수 있습니다. [Linux `sched(7)`](https://man7.org/linux/man-pages/man7/sched.7.html) · [Linux 태스크 상태 구현](https://github.com/torvalds/linux/blob/master/include/linux/sched.h)

**꼬리 질문 · Linux에서 `ps`에 보이는 `R`, `S`, `D`, `Z`는 무엇인가요?**

`R`은 CPU에서 실행 중이거나 실행 가능한 상태입니다. `S`는 시그널로 깨울 수 있는 대기 상태이고, `D`는 I/O 완료 등 특정 조건을 기다리는 인터럽트 불가 대기 상태입니다. `Z`는 종료 후 부모가 종료 상태를 수거할 때까지 최소 정보가 남는 좀비 상태입니다. 일반적인 경우 부모가 `wait()`나 `waitpid()`를 호출하면 해당 정보가 해제됩니다. 스레드별 상태는 `ps -L -p <PID> -o pid,tid,stat,comm`으로 확인합니다. [Linux `ps(1)`](https://man7.org/linux/man-pages/man1/ps.1.html) · [Linux `wait(2)`](https://man7.org/linux/man-pages/man2/wait.2.html)

## 5. 프로세스의 메모리 구조를 설명해 주세요.

**30–60초 답변**

> 프로세스의 가상 주소 공간에는 실행 명령이 담긴 코드 영역, 읽기 전용 데이터, 쓰기 가능한 전역·정적 데이터, 동적 할당에 쓰이는 힙, 스택 등이 있습니다. 일반적인 ELF 프로그램에서는 초기값이 있는 쓰기 가능 전역·정적 변수가 `.data`에, 실행 시작 시 0으로 초기화되는 전역·정적 변수가 주로 `.bss`에 놓입니다. 함수 호출 프레임에는 반환 주소나 지역 변수 등을 저장할 수 있고, 각 스레드는 별도의 스택을 가집니다. 공유 라이브러리와 `mmap()`으로 연 파일도 주소 공간에 매핑될 수 있습니다. 실제 매핑 주소는 실행 파일과 주소 공간 배치 난수화(ASLR) 설정 등에 따라 달라집니다. [Linux `elf(5)`](https://man7.org/linux/man-pages/man5/elf.5.html) · [Linux `proc_pid_maps(5)`](https://man7.org/linux/man-pages/man5/proc_pid_maps.5.html) · [Linux 커널의 ASLR 설정](https://docs.kernel.org/admin-guide/sysctl/kernel.html#randomize-va-space)

**꼬리 질문 · `malloc()`으로 할당한 메모리는 항상 `[heap]`으로 보이나요?**

glibc의 할당기는 힙을 늘리거나 익명 `mmap()` 영역을 사용해 메모리를 확보합니다. 큰 할당은 익명 매핑에 놓일 수 있습니다. `/proc/<PID>/maps`에서 `[heap]`은 특정 매핑의 이름이고, 다른 익명 매핑에도 동적 할당 메모리가 있을 수 있습니다. 파일과 라이브러리 매핑의 읽기·쓰기·실행 권한도 이 파일에서 확인할 수 있습니다. [Linux `malloc(3)`](https://man7.org/linux/man-pages/man3/malloc.3.html) · [Linux `proc_pid_maps(5)`](https://man7.org/linux/man-pages/man5/proc_pid_maps.5.html)

## 6. PCB란 무엇이며 어떤 정보를 담나요?

**30–60초 답변**

> PCB(Process Control Block)는 운영체제가 프로세스를 식별하고 실행과 자원을 관리하는 데 필요한 정보를 담는 자료구조입니다. 대표 항목으로 PID와 부모 정보, 실행 상태와 스케줄링 정보, CPU 사용 시간, 주소 공간과 열린 파일에 대한 참조가 있습니다. 중단된 실행을 재개하려면 프로그램 카운터, 스택 포인터, 레지스터 같은 실행 문맥도 저장해야 합니다. 멀티스레드 운영체제에서는 주소 공간이나 파일처럼 공유하는 자원과 스레드마다 다른 실행 문맥을 구분해 관리합니다. Linux에서는 스레드별 `task_struct`가 스케줄링 정보와 공유 자원에 대한 참조를 가집니다. [Linux `task_struct` 정의](https://github.com/torvalds/linux/blob/master/include/linux/sched.h) · [Linux `proc_pid_stat(5)`](https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html)

**꼬리 질문 · 같은 프로세스의 두 스레드를 전환할 때 무엇이 바뀌나요?**

커널은 나가는 스레드의 재개에 필요한 실행 문맥을 저장하고 들어오는 스레드의 문맥을 복원합니다. 두 스레드가 같은 주소 공간을 쓰므로 그 주소 공간을 계속 사용할 수 있습니다. Linux에서 `/proc/<PID>/task/<TID>/status`를 보면 같은 프로세스에 속해도 스레드별 상태가 달라질 수 있습니다. [Linux `task_struct` 정의](https://github.com/torvalds/linux/blob/master/include/linux/sched.h) · [Linux `proc_pid_task(5)`](https://man7.org/linux/man-pages/man5/proc_pid_task.5.html)

## 7. 시스템 콜과 인터럽트의 차이는 무엇인가요?

**30–60초 답변**

> 시스템 콜은 실행 중인 프로그램이 파일 읽기 같은 커널 서비스를 요청하는 인터페이스입니다. 호출 스레드가 정해진 명령을 실행하면 그 명령에 동기적으로 커널에 진입합니다. 하드웨어 인터럽트는 타이머 만료나 장치의 I/O 완료처럼 현재 실행 중인 명령과 독립적인 사건을 CPU에 알립니다. 인터럽트는 사용자 코드나 커널 코드가 실행 중일 때 발생할 수 있습니다. 사용자 모드에서 커널 모드로 들어가는 것은 CPU 모드 전환이고, 스케줄러가 실행 대상을 다른 스레드로 교체하는 것이 문맥 교환입니다. [Linux 커널의 시스템 콜과 인터럽트 진입 처리](https://docs.kernel.org/core-api/entry.html)

**꼬리 질문 · `read()`를 호출하면 매번 다른 스레드로 전환되나요?**

읽을 데이터가 이미 있는 경우 커널에서 읽기를 완료하고 같은 스레드가 사용자 모드에서 실행을 이어갈 수 있습니다. 블로킹 읽기에서 데이터가 아직 없으면 호출 스레드가 대기하고 스케줄러가 다른 실행 가능한 스레드를 선택할 수 있습니다. 장치가 인터럽트로 완료를 알리면 커널이 대기 중인 스레드를 깨울 수 있고, 그 스레드는 다시 스케줄링될 때 읽기 호출을 이어갑니다. [Linux 커널의 진입·복귀 처리](https://docs.kernel.org/core-api/entry.html) · [Linux `sched(7)`](https://man7.org/linux/man-pages/man7/sched.7.html)
