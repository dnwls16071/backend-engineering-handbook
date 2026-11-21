# Configuring Container Storage and Optimizing Docker Builds

컨테이너에 접속할 주소, 실행할 때 전달할 설정, 컨테이너를 교체할 때 남겨야 할 데이터를 차례로 구분한다. 마지막에는 같은 웹 페이지를 Dockerfile로 빌드하면서 어떤 단계가 캐시되고 최종 이미지에 어떤 파일이 들어가는지 확인한다.

로컬 Docker에서 같은 터미널로 실습을 이어 간다. 예제 이미지는 `nginx:1.27-alpine`, `alpine:3.20`, `mysql:8.4` 태그를 사용한다. 호스트 포트는 Docker가 자동으로 할당하고, 컨테이너와 볼륨 이름에는 실습마다 생성한 접두사를 붙인다.

## 1. 호스트 포트와 컨테이너 포트 매핑

`-p 호스트주소:호스트포트:컨테이너포트`는 호스트 주소와 포트로 들어온 트래픽을 컨테이너의 해당 포트로 전달한다. 예를 들어 `-p 127.0.0.1:8080:80`이면 호스트의 `127.0.0.1:8080`이 컨테이너의 `80/tcp`에 연결된다. 실습에서는 호스트 주소를 `127.0.0.1`로 지정하고 포트 자리를 비워 빈 포트를 할당받는다. 호스트 주소를 생략하면 Docker의 기본 설정에서 모든 호스트 인터페이스에 포트를 게시한다.

```sh
lab_dir="$(mktemp -d "${TMPDIR:-/tmp}/lounge-docker-s4.XXXXXXXX")"
lab_name="${lab_dir##*/}"
web_container="${lab_name}-nginx"

docker run --detach --rm --name "$web_container" \
    --publish 127.0.0.1::80 nginx:1.27-alpine
docker port "$web_container" 80/tcp
web_address="$(docker port "$web_container" 80/tcp)"
curl --fail --retry 5 --retry-all-errors --retry-delay 1 "http://$web_address/"
docker stop "$web_container"
```

`docker port`는 `127.0.0.1:<할당된 포트>`를 출력한다. `curl`로 요청하면 Nginx 기본 페이지가 반환된다. 마지막 `docker stop`에서 `--rm`으로 시작한 컨테이너도 함께 삭제된다.

Dockerfile의 `EXPOSE 80`은 이미지가 사용하는 컨테이너 포트를 메타데이터에 기록한다. `docker image inspect --format '{{json .Config.ExposedPorts}}' nginx:1.27-alpine`으로 이 선언을 확인할 수 있다. 호스트 포트 게시는 `docker run -p`로 지정하며, `-P`는 `EXPOSE`나 `--expose`로 선언된 포트를 무작위 호스트 포트에 게시한다. 컨테이너에서 실제로 포트를 열고 요청을 받는 일은 애플리케이션이 담당한다. [포트 게시와 매핑](https://docs.docker.com/engine/network/port-publishing/) · [Dockerfile EXPOSE](https://docs.docker.com/reference/dockerfile/#expose)

## 2. 환경 변수를 전달하고 MySQL 접속하기

`docker run -e NAME=value`와 `docker run --env NAME=value`는 컨테이너에 환경 변수를 설정한다. `-e NAME`은 호스트에서 내보낸 `NAME` 값을 전달한다. 여러 변수를 관리할 때는 `NAME=value`를 한 줄에 하나씩 적고 `--env-file`로 읽는다. 두 옵션 모두 이미지의 `ENV` 기본값을 덮어쓸 수 있다. `--env-file`로 전달한 값도 컨테이너의 환경에 저장되므로 Docker에 접근할 수 있는 사용자는 설정을 조회할 수 있다.

```sh
docker run --rm --env APP_ENV=local alpine:3.20 printenv APP_ENV
```

MySQL 공식 이미지는 빈 데이터 디렉터리로 처음 시작할 때 아래 변수로 데이터베이스와 계정을 만든다. 이 예제의 비밀번호는 실습 전용이다. MySQL 데이터 파일은 컨테이너의 `/var/lib/mysql`에 쓰이며, 실습에서는 그 경로에 이름 있는 볼륨을 마운트한다.

```sh
mysql_container="${lab_name}-mysql"
mysql_volume="${lab_name}-mysql-data"
mysql_env="$lab_dir/mysql.env"

(
    umask 077
    cat > "$mysql_env" <<'ENV'
MYSQL_ROOT_PASSWORD=lab-root-only-84
MYSQL_DATABASE=lounge_lab
MYSQL_USER=lounge_user
MYSQL_PASSWORD=lab-user-only-84
ENV
)

docker volume create "$mysql_volume"
docker run --detach --name "$mysql_container" \
    --env-file "$mysql_env" \
    --publish 127.0.0.1::3306 \
    --mount "type=volume,src=$mysql_volume,dst=/var/lib/mysql" \
    mysql:8.4
docker logs --follow "$mysql_container"
```

첫 실행에는 초기화 시간이 필요하다. `MySQL init process done. Ready for start up.` 이후 `port: 3306`을 포함한 `ready for connections` 로그가 나오면 `Ctrl+C`로 로그 추적을 끝낸다. 호스트에 `mysql` 클라이언트가 있으면 게시된 포트로 접속한다. 비밀번호 프롬프트에는 `MYSQL_PASSWORD` 값을 입력한다.

```sh
mysql_address="$(docker port "$mysql_container" 3306/tcp)"
mysql --protocol=TCP -h 127.0.0.1 -P "${mysql_address##*:}" -u lounge_user -p lounge_lab
```

호스트에 클라이언트가 없으면 컨테이너 이미지에 포함된 `mysql`을 사용한다. 이 명령의 `127.0.0.1`과 `3306`은 컨테이너 내부의 주소와 포트다.

```sh
docker exec -it "$mysql_container" \
    mysql --protocol=TCP -h 127.0.0.1 -P 3306 -u lounge_user -p lounge_lab
```

접속한 클라이언트에서 행을 추가하고 읽는다. `exit`로 클라이언트를 종료하고 컨테이너와 볼륨은 5절까지 유지한다.

```sql
CREATE TABLE IF NOT EXISTS notes (id INT PRIMARY KEY, label VARCHAR(40));
INSERT INTO notes VALUES (1, 'first run') ON DUPLICATE KEY UPDATE label = 'first run';
SELECT id, label FROM notes;
```

[Docker run 환경 변수 옵션](https://docs.docker.com/reference/cli/docker/container/run/#env) · [MySQL 공식 이미지 환경 변수와 초기화](https://hub.docker.com/_/mysql)

## 3. 컨테이너 쓰기 레이어의 수명

같은 이미지로 실행해도 컨테이너마다 독립된 쓰기 레이어가 생긴다. 마운트하지 않은 경로에서 파일을 만들거나 수정하면 변경분은 이 레이어에 남는다. `docker stop` 후 `docker start`는 같은 컨테이너를 재사용하고, `docker rm`은 컨테이너와 그 쓰기 레이어를 함께 제거한다.

```sh
layer_container="${lab_name}-layer"
docker run --detach --name "$layer_container" alpine:3.20 sleep 3600
docker exec "$layer_container" sh -c 'echo first-container > /tmp/layer.txt'

docker stop "$layer_container"
docker start "$layer_container"
docker exec "$layer_container" cat /tmp/layer.txt

docker stop "$layer_container"
docker rm "$layer_container"
docker run --rm --name "$layer_container" alpine:3.20 \
    sh -c 'test ! -e /tmp/layer.txt && echo missing-in-new-container'
```

같은 컨테이너를 다시 시작하면 `first-container`가 출력된다. 컨테이너를 삭제한 뒤 같은 이미지와 같은 이름으로 새로 만들면 `missing-in-new-container`가 출력된다. [이미지 레이어와 컨테이너 레이어](https://docs.docker.com/engine/storage/drivers/)

## 4. 바인드 마운트와 볼륨 마운트

두 마운트 모두 데이터의 수명을 컨테이너의 쓰기 레이어와 분리한다. 바인드 마운트는 호스트에서 지정한 파일이나 디렉터리를 연결하고, 이름 있는 볼륨은 Docker가 관리하는 저장 공간을 이름으로 연결한다.

| 마운트 종류 | `--mount` 형식 | 사용하는 경우 |
| --- | --- | --- |
| 바인드 마운트 | `type=bind,src=호스트경로,dst=컨테이너경로` | 호스트 편집기로 수정하는 소스 코드나 설정 파일을 공유할 때 |
| 이름 있는 볼륨 | `type=volume,src=볼륨이름,dst=컨테이너경로` | MySQL 데이터처럼 컨테이너를 교체해도 Docker에서 계속 관리할 데이터가 있을 때 |

다음 실습에서는 호스트 파일을 읽기 전용으로 마운트한다. 서로 다른 컨테이너가 같은 호스트 경로를 읽으므로 두 번째 실행에는 호스트에서 바꾼 내용이 표시된다.

```sh
bind_dir="$lab_dir/shared"
mkdir "$bind_dir"
printf 'version 1\n' > "$bind_dir/message.txt"

docker run --rm --mount "type=bind,src=$bind_dir,dst=/shared,readonly" \
    alpine:3.20 cat /shared/message.txt

printf 'version 2\n' > "$bind_dir/message.txt"
docker run --rm --mount "type=bind,src=$bind_dir,dst=/shared,readonly" \
    alpine:3.20 cat /shared/message.txt
```

바인드 마운트의 원본은 Docker 데몬이 접근할 수 있는 경로여야 한다. `--mount type=bind`는 기본적으로 원본 경로가 없으면 오류를 반환한다. 컨테이너에 이미 파일이 있는 경로에 마운트하면 마운트가 연결된 동안 원래 파일은 그 경로에서 가려진다. 빈 볼륨을 마운트할 때는 기본적으로 컨테이너 경로의 기존 파일을 볼륨에 복사하며, `volume-nocopy`를 지정하면 이 복사를 끌 수 있다. [바인드 마운트](https://docs.docker.com/engine/storage/bind-mounts/) · [볼륨](https://docs.docker.com/engine/storage/volumes/)

## 5. 이름 있는 볼륨을 재사용하고 정리하기

2절에서 `docker volume create`로 만든 볼륨은 `docker volume inspect`로 확인할 수 있다. 기존 MySQL 컨테이너를 정상 종료하고 삭제한 뒤 새 컨테이너에 같은 볼륨을 붙인다. 이번에는 초기화용 데이터베이스 이름을 `lounge_recreated`로 전달한다.

```sh
docker volume inspect "$mysql_volume"
docker stop "$mysql_container"
docker rm "$mysql_container"

docker run --detach --name "$mysql_container" \
    --env MYSQL_DATABASE=lounge_recreated \
    --publish 127.0.0.1::3306 \
    --mount "type=volume,src=$mysql_volume,dst=/var/lib/mysql" \
    mysql:8.4
docker logs --follow "$mysql_container"
```

이번에는 이미 초기화한 데이터 디렉터리를 사용하므로 `port: 3306`을 포함한 `ready for connections` 로그를 기다린다. `Ctrl+C`로 로그 추적을 끝내고 2절의 `docker exec` 명령으로 다시 접속한다. 호스트 클라이언트를 사용한다면 `docker port`로 새 포트를 읽는다. 계정과 비밀번호는 2절과 같다.

```sql
SELECT id, label FROM notes;
```

`1`, `first run` 행이 남아 있다. 클라이언트에서 `exit`로 나온 뒤 새 스키마가 생겼는지 컨테이너 내부에서 관리자 권한으로 확인한다. 프롬프트에는 2절의 `MYSQL_ROOT_PASSWORD`를 입력한다.

```sh
docker exec -it "$mysql_container" mysql -u root -p \
    -e "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = 'lounge_recreated'"
```

스키마 조회 결과는 비어 있다. MySQL 공식 이미지의 `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`는 데이터 디렉터리를 처음 초기화할 때 적용된다. 이미 초기화한 볼륨의 스키마나 계정을 바꾸려면 실행 중인 서버에서 SQL로 변경한다.

실습 컨테이너와 볼륨을 삭제한다. 볼륨을 삭제하면 이 실습에서 기록한 MySQL 데이터도 사라진다.

```sh
docker stop "$mysql_container"
docker rm "$mysql_container"
docker volume rm "$mysql_volume"
rm "$mysql_env" "$bind_dir/message.txt"
rmdir "$bind_dir"
```

[볼륨 관리](https://docs.docker.com/engine/storage/volumes/) · [기존 데이터 디렉터리로 MySQL 실행](https://hub.docker.com/_/mysql)

## 6. Dockerfile과 빌드 컨텍스트

`docker build`의 마지막 인수는 빌드 컨텍스트다. `COPY`의 원본 경로는 이 컨텍스트를 기준으로 해석한다. `--file`은 읽을 Dockerfile을 따로 지정한다. 컨텍스트 루트에 `.dockerignore`를 두면 빌더에 필요 없는 파일을 제외할 수 있다. 다음 예제는 실습 전용 디렉터리에서 `index.html`을 그대로 복사해 이미지를 만든다.

```sh
build_dir="$lab_dir/site"
site_image="lounge-docker-s4-site:$lab_name"
mkdir "$build_dir"

cat > "$build_dir/.dockerignore" <<'IGNORE'
.git
.env
*.log
IGNORE

printf '<h1>Docker storage lab</h1>\n' > "$build_dir/index.html"
cat > "$build_dir/Dockerfile" <<'DOCKERFILE'
FROM nginx:1.27-alpine
COPY index.html /usr/share/nginx/html/index.html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
DOCKERFILE

docker build --tag "$site_image" "$build_dir"
docker run --rm --entrypoint cat "$site_image" /usr/share/nginx/html/index.html
```

`FROM`은 기반 이미지를 선택하고 `COPY`는 파일을 이미지에 넣는다. `EXPOSE`는 서버가 사용하는 포트를 기록하고 `CMD`는 컨테이너를 시작할 때 실행할 기본 명령을 지정한다. Dockerfile에서 `RUN`으로 선언한 명령은 이미지를 빌드할 때 실행된다. 이 실습의 `--entrypoint cat`은 기본 시작 명령을 검사 명령으로 바꿔 이미지에 들어간 HTML을 확인한다. [Dockerfile 명령어](https://docs.docker.com/reference/dockerfile/) · [빌드 컨텍스트와 `.dockerignore`](https://docs.docker.com/build/concepts/context/)

## 7. 빌드 캐시와 멀티 스테이지 빌드

빌더는 각 단계의 명령과 입력을 비교해 이전 결과를 재사용한다. 예를 들어 `COPY title.txt .`의 파일 내용이 바뀌면 해당 `COPY`와 이어지는 렌더링 단계가 다시 실행된다. 자주 바뀌는 파일을 나중에 복사하면 앞에서 한 작업을 재사용할 수 있다. 애플리케이션 이미지에서도 의존성 버전과 잠금 파일을 먼저 복사해 설치하고, 그 다음 소스 코드를 복사하는 이유다.

멀티 스테이지 빌드는 `FROM`을 여러 번 사용해 빌드와 실행 환경을 나눈다. 다음에는 Alpine에서 HTML을 만들고 `COPY --from=build`로 생성된 HTML만 Nginx 이미지로 가져온다.

```sh
cat > "$build_dir/render.sh" <<'SH'
#!/bin/sh
printf '<h1>%s</h1>\n' "$(cat "$1")"
SH
printf 'Docker build cache v1\n' > "$build_dir/title.txt"

cat > "$build_dir/Dockerfile" <<'DOCKERFILE'
FROM alpine:3.20 AS build
WORKDIR /src
COPY render.sh .
RUN sh -n render.sh && mkdir -p /out
COPY title.txt .
RUN sh render.sh title.txt > /out/index.html

FROM nginx:1.27-alpine AS runtime
COPY --from=build /out/index.html /usr/share/nginx/html/index.html
DOCKERFILE

docker build --progress=plain --tag "$site_image" "$build_dir"
printf 'Docker build cache v2\n' > "$build_dir/title.txt"
docker build --progress=plain --tag "$site_image" "$build_dir"
docker run --rm --entrypoint cat "$site_image" /usr/share/nginx/html/index.html
```

두 번째 빌드에서 `COPY render.sh .`과 `RUN sh -n render.sh && mkdir -p /out`은 `CACHED`로 표시된다. `title.txt`를 복사하고 HTML을 만드는 단계는 다시 실행되며 최종 이미지의 `cat` 출력에는 `Docker build cache v2`가 나온다. 마지막 단계는 `build` 단계에서 `/out/index.html` 한 파일만 가져오기 때문에 렌더링 스크립트와 제목 원본은 빌드 단계에 머문다.

```sh
docker image rm "$site_image"
rm "$build_dir/Dockerfile" "$build_dir/.dockerignore" "$build_dir/index.html" \
    "$build_dir/render.sh" "$build_dir/title.txt"
rmdir "$build_dir" "$lab_dir"
```

[빌드 캐시 무효화](https://docs.docker.com/build/cache/invalidation/) · [캐시 사용 최적화](https://docs.docker.com/build/cache/optimize/) · [멀티 스테이지 빌드](https://docs.docker.com/build/building/multi-stage/)
