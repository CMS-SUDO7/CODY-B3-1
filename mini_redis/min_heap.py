"""TTL 만료 시각을 빠르게 찾기 위한 최소 힙."""


class MinHeap:
    """비교 가능한 값을 저장하는 배열 기반 최소 힙."""

    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)
        self._heapify_up(len(self.items) - 1)

    def pop(self):
        if not self.items:
            return None
        root = self.items[0]
        last = self.items.pop()
        if self.items:
            self.items[0] = last
            self._heapify_down(0)
        return root

    def peek(self):
        if not self.items:
            return None
        return self.items[0]

    def size(self):
        return len(self.items)

    def _heapify_up(self, index):
        while index > 0:
            parent = (index - 1) // 2
            if self.items[parent] <= self.items[index]:
                break
            self.items[parent], self.items[index] = (
                self.items[index],
                self.items[parent],
            )
            index = parent

    def _heapify_down(self, index):
        length = len(self.items)
        while True:
            left = index * 2 + 1
            right = left + 1
            smallest = index

            if left < length and self.items[left] < self.items[smallest]:
                smallest = left
            if right < length and self.items[right] < self.items[smallest]:
                smallest = right
            if smallest == index:
                break

            self.items[index], self.items[smallest] = (
                self.items[smallest],
                self.items[index],
            )
            index = smallest
