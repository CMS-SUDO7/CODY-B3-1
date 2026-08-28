# CLI Mini Redis

Python의 `dict`, `set`, `collections` 없이 해시맵, 이중 연결 리스트, 최소 힙을 직접 구현한 학습용 인메모리 Key-Value 저장소입니다. 네트워크 통신과 파일 저장 없이 CLI에서 동작합니다.

## 1. 실행 방법

Python 3.8 이상만 필요하며 외부 패키지는 없습니다.

```bash
cd mini_redis_project
python3 main.py
```

종료는 `exit`, `quit`, `Ctrl+C`, `Ctrl+D` 중 하나를 사용합니다.

```text
mini-redis> SET name "Alice Kim"
OK
mini-redis> GET name
"Alice Kim"
mini-redis> EXPIRE name 10
(integer) 1
mini-redis> TTL name
(integer) 10
mini-redis> INFO memory
used_memory:13
maxmemory:0
evicted_keys:0
mini-redis> quit
```

테스트 실행:

```bash
python3 -m unittest discover -v
```

## 2. 파일·클래스 구조

```text
mini_redis_project/
├── main.py                     # 프로그램 시작점
├── mini_redis/
│   ├── linked_list.py          # ListNode, DoublyLinkedList
│   ├── hash_map.py             # HashEntry, HashMap
│   ├── min_heap.py             # MinHeap
│   ├── database.py             # MiniRedis 핵심 기능
│   └── cli.py                  # 명령 파싱·검증·REPL
└── tests/
    ├── test_structures.py      # 세 자료구조 단위 테스트
    └── test_database.py        # 명령·LRU·TTL 통합 테스트
```

역할의 경계를 이렇게 나누면 자료구조 자체의 오류와 Redis 명령 조합 과정의 오류를 따로 찾을 수 있습니다.

## 3. 내부 구조와 데이터 흐름

| 구조 | 저장 내용 | 목적 | 주요 복잡도 |
|---|---|---|---|
| `data: HashMap` | key → value | 실제 문자열 데이터 | 평균 조회·저장·삭제 O(1) |
| `lru: DoublyLinkedList` | 최근 사용 순서의 key | 뒤쪽 LRU 키 즉시 선택 | 이동·양 끝 삭제 O(1) |
| `lru_nodes: HashMap` | key → LRU 노드 | 리스트 노드를 즉시 찾음 | 평균 O(1) |
| `expires: HashMap` | key → 현재 expire_at | 활성 TTL 판별 | 평균 O(1) |
| `expire_heap: MinHeap` | (expire_at, key) | 가장 빠른 만료 조회 | push/pop O(log N), peek O(1) |

LRU 리스트의 `head`는 가장 최근에 사용한 키(MRU), `tail`은 가장 오래 사용하지 않은 키(LRU)입니다. `SET`과 성공한 `GET`은 키를 head로 이동합니다. 메모리가 넘으면 tail부터 제거합니다.

TTL은 lazy deletion을 사용합니다. 같은 키에 `EXPIRE`를 여러 번 적용하거나 `DEL`하면 힙에 과거 항목이 남을 수 있습니다. 그러나 `expires`에 기록된 현재 만료 시각과 일치하는 항목만 유효하므로, 오래된 힙 항목은 루트에 도착했을 때 버립니다. 따라서 힙 중간을 O(N)으로 검색해 지울 필요가 없습니다.

## 4. 명령어 요약

| 명령 | 정상 결과 | 중요한 규칙 |
|---|---|---|
| `SET key value` | `OK` | LRU 갱신, 덮어쓰기 시 TTL 삭제 |
| `GET key` | `"value"` 또는 `(nil)` | 성공했을 때만 LRU 갱신 |
| `DEL key` | `(integer) 1/0` | 데이터·LRU·활성 TTL 동시 제거 |
| `EXISTS key` | `(integer) 1/0` | 먼저 만료 정리 |
| `DBSIZE` | `(integer) N` | 만료된 키 제외 |
| `KEYS` | 번호가 붙은 키 목록 | 패턴 매칭·정렬 없음 |
| `CONFIG SET maxmemory bytes` | `OK` | 0은 무제한, 축소 시 즉시 LRU 제거 |
| `INFO memory` | 메모리 관련 3개 항목 | UTF-8 바이트 길이로 계산 |
| `EXPIRE key seconds` | `(integer) 1/0` | 0 이하는 즉시 삭제 |
| `TTL key` | N, -1, -2 | -1은 TTL 없음, -2는 키 없음 |

### 명령별 반환 형식과 엣지 케이스

| 명령 | 정상 예시 | 없는 키·경계 조건 | 오류 사례 |
|---|---|---|---|
| `SET name Alice` | `OK` | 기존 키면 값을 바꾸고 TTL 삭제 | 단일 엔트리가 제한보다 크면 `(error) OOM ...` |
| `GET name` | `"Alice"` | 없거나 만료되면 `(nil)` | 인자 수가 다르면 `(error) ERR wrong number ...` |
| `DEL name` | `(integer) 1` | 없거나 이미 만료되면 `(integer) 0` | 인자 수 오류 |
| `EXISTS name` | `(integer) 1` | 없거나 이미 만료되면 `(integer) 0` | 인자 수 오류 |
| `DBSIZE` | `(integer) 3` | 만료 키를 정리한 뒤 계산 | 인자가 있으면 인자 수 오류 |
| `KEYS` | `1. "name"` 형태 | 키가 없으면 `(empty array)` | 인자가 있으면 인자 수 오류 |
| `CONFIG SET maxmemory 100` | `OK` | `0`은 무제한, 제한 축소 시 즉시 eviction | 음수·비정수는 정수 오류 |
| `INFO memory` | 아래의 고정된 3줄 | 명령 전에 만료 정리 | 다른 section은 `(error) ERR ...` |
| `EXPIRE name 10` | `(integer) 1` | 없는 키는 `0`, 0 이하는 즉시 삭제 후 `1` | seconds가 비정수면 정수 오류 |
| `TTL name` | `(integer) N` | TTL 없음 `-1`, 키 없음·만료 `-2` | 인자 수 오류 |

`INFO memory`는 항목 순서와 줄바꿈까지 다음 형식으로 고정하며 테스트에서도 문자열 전체를 비교합니다.

```text
used_memory:9
maxmemory:100
evicted_keys:0
```

모든 오류는 `(error) `로 시작합니다. 지원하는 명령의 인자 수 오류는 `ERR wrong number ...`, 알 수 없는 명령은 `ERR unknown command ...`, 정수 변환 실패는 `ERR value is not an integer or out of range`, 단일 엔트리 초과는 `OOM ...` 형식을 사용합니다.

## 5. 공식 메모리 계산과 OOM

```text
used_memory = 모든 키에 대해 Σ(UTF-8 key 바이트 수 + UTF-8 value 바이트 수)
```

예를 들어 `SET name Alice`는 `name` 4바이트 + `Alice` 5바이트로 9바이트입니다. 한글은 UTF-8에서 보통 글자당 3바이트이므로 문자 개수와 바이트 수가 다를 수 있습니다.

새 단일 엔트리 자체가 `maxmemory`보다 크면 기존 값을 건드리지 않고 OOM을 반환합니다. 단일 엔트리는 들어갈 수 있지만 전체 합계가 제한을 넘으면 새 키를 MRU로 표시한 뒤 LRU 키부터 제한 이하가 될 때까지 제거합니다.

### Eviction 처리 순서와 경계 조건

`SET` 또는 더 작은 `maxmemory` 설정으로 제한을 초과하면 다음 순서로 동작합니다.

1. 만료된 키를 먼저 삭제하여 실제 살아 있는 데이터만 남긴다.
2. SET 대상 단일 엔트리가 제한보다 큰지 검사한다. 크다면 기존 값과 TTL을 그대로 보존하고 OOM을 반환한다.
3. 덮어쓰기라면 기존 엔트리 바이트를 `used_memory`에서 뺀다.
4. 새 값을 저장하고 새 엔트리 바이트를 더한 뒤 해당 키를 MRU로 만든다.
5. `used_memory > maxmemory`인 동안 tail의 LRU 키를 삭제한다.
6. 한 키를 지울 때 key+value 바이트를 `used_memory`에서 빼고 `evicted_keys`를 1 증가시킨다.
7. TTL 만료와 사용자의 `DEL`은 메모리 부족에 의한 제거가 아니므로 `evicted_keys`를 증가시키지 않는다.

별도의 eviction 로그는 구현하지 않았습니다. 원래 요구사항에 없고, REPL 표준 출력에 로그를 섞으면 Redis 스타일 반환값을 자동 채점하기 어려워지기 때문입니다. 제거 결과는 `INFO memory`의 `used_memory`와 `evicted_keys`로 확인합니다.

## 6. LRU를 LFU로 바꾼다면

LFU(Least Frequently Used)는 “가장 오래 안 쓴 키”가 아니라 “사용 횟수가 가장 적은 키”를 제거합니다. 이는 원 미션의 구현 요구사항이 아니므로 실제 코드에는 추가하지 않았지만, 변경하려면 다음 재설계가 필요합니다.

| 항목 | 현재 LRU | LFU 변경안 |
|---|---|---|
| 키별 메타데이터 | 리스트 노드 | `frequency`, 같은 빈도 안의 순서 노드 |
| SET/GET 갱신 | 노드를 head로 이동 | frequency를 1 증가시키고 다음 빈도 그룹으로 이동 |
| 제거 대상 | 전체 리스트의 tail | 가장 작은 frequency 그룹의 가장 오래된 키 |
| 핵심 구조 | key→node 해시맵 + 리스트 1개 | key→entry 해시맵 + frequency→리스트 해시맵 + `min_frequency` |

단순히 `(frequency, key)` 최소 힙을 사용할 수도 있지만 GET마다 우선순위가 바뀌어 오래된 힙 항목을 lazy deletion으로 처리해야 합니다. 평균 O(1)을 목표로 한다면 빈도별 이중 연결 리스트와 `min_frequency` 조합이 적합합니다. 빈도가 같을 때는 LRU 순서로 제거하면 동점 정책도 명확해집니다. 장기 사용 키의 빈도만 계속 커지는 문제에는 주기적인 frequency 감소 또는 aging 정책이 필요합니다.

## 7. 키 10만 개 이상으로 확장한다면

10만 개가 되더라도 해시맵의 단일 조회는 평균 O(1)이지만, 시스템 전체에는 다음 병목이 생길 수 있습니다.

| 예상 병목 | 원인 | 대응 설계 |
|---|---|---|
| 해시맵 resize 순간 정지 | 전체 N개 rehash가 한 번에 O(N) | 점진적 rehash 또는 미리 capacity 확보 |
| 실제 메모리 증가 | Python 객체·노드·버킷 오버헤드 | 더 작은 객체 표현, 메모리 측정, 용량 계획 |
| TTL 힙 팽창 | EXPIRE 재설정의 stale 항목 누적 | 주기적 힙 compaction 또는 세대 번호 사용 |
| `KEYS` 지연과 큰 출력 | 모든 키 순회와 문자열 I/O가 O(N) | cursor 기반 SCAN 형태로 나누어 반환 |
| 단일 실행 흐름 | 긴 명령 동안 다른 명령 처리 불가 | 작업을 작은 단위로 나누거나 shard별 프로세스 운영 |
| 한 저장소의 CPU·메모리 한계 | 모든 키가 한 인스턴스에 집중 | 키 해시 기반 샤딩 |

샤딩은 예를 들어 `hash(key) % shard_count`로 담당 저장소를 나누는 방식입니다. 각 shard가 독립적인 `MiniRedis`와 메모리 제한을 가지면 서로 다른 shard를 병렬 처리할 수 있습니다. 다만 shard 수 변경 시 많은 키가 이동하고, 여러 키를 동시에 다루는 명령과 전체 `DBSIZE` 집계가 복잡해집니다. 실제 구현에는 네트워크, 동시성, 장애 복구까지 필요하지만 이는 “CLI 전용·동시성 제외”라는 원 미션 범위를 크게 넘으므로 이번 결과물에는 설계 설명만 포함했습니다.

cd mini_redis_project
python3 main.py
