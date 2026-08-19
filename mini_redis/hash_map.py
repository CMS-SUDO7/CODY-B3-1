"""체이닝과 자동 확장을 직접 구현한 해시맵."""

from .linked_list import DoublyLinkedList


class HashEntry:
    """체이닝 버킷에 저장되는 키-값 한 쌍."""

    def __init__(self, key, value):
        self.key = key
        self.value = value


class HashMap:
    """문자열 키를 저장하는 체이닝 방식 해시맵.

    버킷은 고정 길이 배열(list)이며 각 버킷의 충돌 항목은 직접 구현한
    DoublyLinkedList에 연결한다. 로드 팩터가 0.75를 넘으면 두 배로 확장한다.
    """

    def __init__(self, initial_capacity=8):
        if initial_capacity < 1:
            initial_capacity = 1
        self.capacity = initial_capacity
        self.buckets = [None] * self.capacity
        self.count = 0

    def _hash(self, key):
        """UTF-8 바이트를 대상으로 한 64비트 FNV-1a 해시 함수."""
        hash_value = 14695981039346656037
        for byte in key.encode("utf-8"):
            hash_value ^= byte
            hash_value = (hash_value * 1099511628211) & 0xFFFFFFFFFFFFFFFF
        return hash_value

    def _index(self, key):
        return self._hash(key) % self.capacity

    def _find_node(self, key):
        bucket = self.buckets[self._index(key)]
        if bucket is None:
            return None
        current = bucket.head
        while current is not None:
            if current.data.key == key:
                return current
            current = current.next
        return None

    def put(self, key, value):
        node = self._find_node(key)
        if node is not None:
            old_value = node.data.value
            node.data.value = value
            return old_value

        index = self._index(key)
        if self.buckets[index] is None:
            self.buckets[index] = DoublyLinkedList()
        self.buckets[index].insert_back(HashEntry(key, value))
        self.count += 1

        if self.count / self.capacity > 0.75:
            self._resize(self.capacity * 2)
        return None

    def get(self, key):
        node = self._find_node(key)
        if node is None:
            return None
        return node.data.value

    def remove(self, key):
        index = self._index(key)
        bucket = self.buckets[index]
        if bucket is None:
            return None

        current = bucket.head
        while current is not None:
            if current.data.key == key:
                value = current.data.value
                bucket.remove_node(current)
                self.count -= 1
                if bucket.size() == 0:
                    self.buckets[index] = None
                return value
            current = current.next
        return None

    def contains(self, key):
        return self._find_node(key) is not None

    def keys(self):
        result = []
        for bucket in self.buckets:
            if bucket is None:
                continue
            current = bucket.head
            while current is not None:
                result.append(current.data.key)
                current = current.next
        return result

    def size(self):
        return self.count

    def _resize(self, new_capacity):
        old_buckets = self.buckets
        self.capacity = new_capacity
        self.buckets = [None] * self.capacity
        old_count = self.count
        self.count = 0

        for bucket in old_buckets:
            if bucket is None:
                continue
            current = bucket.head
            while current is not None:
                self.put(current.data.key, current.data.value)
                current = current.next

        self.count = old_count
