"""String, LRU, TTL, 메모리 제한을 결합한 Mini Redis 핵심 로직."""

import math
import time

from .hash_map import HashMap
from .linked_list import DoublyLinkedList
from .min_heap import MinHeap


class MiniRedis:
    """네트워크와 영속성을 제외한 학습용 인메모리 Key-Value 저장소."""

    INTEGER_ERROR = "(error) ERR value is not an integer or out of range"
    OOM_ERROR = "(error) OOM command not allowed when used_memory > 'maxmemory'"

    def __init__(self, clock=None):
        # 실제 문자열 데이터: key -> value
        self.data = HashMap()
        # LRU 책임 분리: 리스트는 사용 순서, 해시맵은 key -> 리스트 노드 탐색
        self.lru = DoublyLinkedList()
        self.lru_nodes = HashMap()
        # TTL 책임 분리: 해시맵은 활성 TTL, 최소 힙은 가장 이른 만료 탐색
        self.expires = HashMap()
        self.expire_heap = MinHeap()
        self.used_memory = 0
        self.maxmemory = 0
        self.evicted_keys = 0
        self._clock = clock if clock is not None else time.time

    @staticmethod
    def _entry_size(key, value):
        return len(key.encode("utf-8")) + len(value.encode("utf-8"))

    def _touch(self, key):
        node = self.lru_nodes.get(key)
        if node is None:
            node = self.lru.insert_front(key)
            self.lru_nodes.put(key, node)
        else:
            self.lru.move_to_front(node)

    def _delete_key(self, key):
        """데이터, 메모리, LRU, 활성 TTL 정보를 한 번에 제거한다."""
        if not self.data.contains(key):
            return False

        value = self.data.remove(key)
        self.used_memory -= self._entry_size(key, value)

        node = self.lru_nodes.remove(key)
        if node is not None:
            self.lru.remove_node(node)

        # 힙의 과거 항목은 lazy deletion으로 남을 수 있지만 활성 TTL은 제거된다.
        self.expires.remove(key)
        return True

    def _purge_expired(self):
        """힙의 루트부터 현재 시각에 만료된 활성 TTL을 제거한다."""
        now = self._clock()
        while self.expire_heap.size() > 0:
            expire_at, key = self.expire_heap.peek()
            if expire_at > now:
                break
            self.expire_heap.pop()
            active_expire_at = self.expires.get(key)
            if active_expire_at is None or active_expire_at != expire_at:
                continue
            self._delete_key(key)

    def _evict_if_needed(self):
        """제한 이하가 될 때까지 tail(LRU)을 제거하고 통계를 갱신한다.

        TTL 만료나 사용자의 DEL은 eviction이 아니므로 evicted_keys를 올리지
        않는다. 별도 로그는 Redis 스타일 명령 출력과 섞이지 않도록 남기지 않는다.
        """
        while self.maxmemory > 0 and self.used_memory > self.maxmemory:
            if self.lru.tail is None:
                break
            key = self.lru.tail.data
            self._delete_key(key)
            self.evicted_keys += 1

    def set(self, key, value):
        self._purge_expired()
        new_size = self._entry_size(key, value)
        if self.maxmemory > 0 and new_size > self.maxmemory:
            return self.OOM_ERROR

        if self.data.contains(key):
            old_value = self.data.get(key)
            self.used_memory -= self._entry_size(key, old_value)

        self.data.put(key, value)
        self.used_memory += new_size
        self.expires.remove(key)  # 덮어쓴 키의 TTL 초기화
        self._touch(key)
        self._evict_if_needed()
        return "OK"

    def get(self, key):
        """만료 정리 후 존재하는 값만 반환하고 그때만 LRU를 갱신한다."""
        self._purge_expired()
        if not self.data.contains(key):
            return "(nil)"
        value = self.data.get(key)
        self._touch(key)
        return '"' + value + '"'

    def delete(self, key):
        self._purge_expired()
        deleted = self._delete_key(key)
        return "(integer) 1" if deleted else "(integer) 0"

    def exists(self, key):
        self._purge_expired()
        return "(integer) 1" if self.data.contains(key) else "(integer) 0"

    def dbsize(self):
        self._purge_expired()
        return "(integer) " + str(self.data.size())

    def keys(self):
        self._purge_expired()
        key_list = self.data.keys()
        if not key_list:
            return "(empty array)"
        lines = []
        index = 1
        for key in key_list:
            lines.append(str(index) + '. "' + key + '"')
            index += 1
        return "\n".join(lines)

    def config_set_maxmemory(self, text):
        try:
            value = int(text)
        except (TypeError, ValueError):
            return self.INTEGER_ERROR
        if value < 0:
            return self.INTEGER_ERROR

        self._purge_expired()
        self.maxmemory = value
        self._evict_if_needed()
        return "OK"

    def info_memory(self):
        self._purge_expired()
        return (
            "used_memory:" + str(self.used_memory) + "\n"
            "maxmemory:" + str(self.maxmemory) + "\n"
            "evicted_keys:" + str(self.evicted_keys)
        )

    def expire(self, key, seconds_text):
        self._purge_expired()
        try:
            seconds = int(seconds_text)
        except (TypeError, ValueError):
            return self.INTEGER_ERROR

        if not self.data.contains(key):
            return "(integer) 0"
        if seconds <= 0:
            self._delete_key(key)
            return "(integer) 1"

        expire_at = self._clock() + seconds
        self.expires.put(key, expire_at)
        self.expire_heap.push((expire_at, key))
        return "(integer) 1"

    def ttl(self, key):
        self._purge_expired()
        if not self.data.contains(key):
            return "(integer) -2"
        expire_at = self.expires.get(key)
        if expire_at is None:
            return "(integer) -1"
        remaining = max(0, math.ceil(expire_at - self._clock()))
        return "(integer) " + str(remaining)
