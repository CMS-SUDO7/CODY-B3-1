import unittest

from mini_redis.hash_map import HashMap
from mini_redis.linked_list import DoublyLinkedList
from mini_redis.min_heap import MinHeap


class DoublyLinkedListTest(unittest.TestCase):
    def assert_list_invariants(self, linked, expected):
        """length, 양방향 연결, head/tail이 같은 내용을 나타내는지 검사한다."""
        forward = []
        current = linked.head
        previous = None
        while current is not None:
            self.assertIs(current.prev, previous)
            forward.append(current.data)
            previous = current
            current = current.next

        backward = []
        current = linked.tail
        following = None
        while current is not None:
            self.assertIs(current.next, following)
            backward.append(current.data)
            following = current
            current = current.prev

        self.assertEqual(forward, expected)
        self.assertEqual(backward, list(reversed(expected)))
        self.assertEqual(linked.size(), len(expected))

    def test_insert_move_and_remove(self):
        linked = DoublyLinkedList()
        first = linked.insert_back("a")
        second = linked.insert_back("b")
        linked.insert_front("z")
        self.assert_list_invariants(linked, ["z", "a", "b"])

        linked.move_to_front(linked.tail)
        self.assertEqual(linked.head.data, "b")
        self.assert_list_invariants(linked, ["b", "z", "a"])

        self.assertEqual(linked.remove_back(), "a")
        self.assertIsNone(first.prev)
        self.assert_list_invariants(linked, ["b", "z"])
        self.assertEqual(linked.remove_node(second), "b")
        self.assert_list_invariants(linked, ["z"])
        self.assertEqual(linked.remove_front(), "z")
        self.assert_list_invariants(linked, [])


class HashMapTest(unittest.TestCase):
    def test_put_get_resize_remove_and_keys(self):
        table = HashMap(2)
        table.put("a", "1")
        table.put("b", "2")
        table.put("c", "3")
        self.assertGreaterEqual(table.capacity, 4)
        self.assertEqual(table.get("b"), "2")
        self.assertTrue(table.contains("c"))
        self.assertEqual(table.remove("a"), "1")
        self.assertFalse(table.contains("a"))
        self.assertEqual(table.size(), 2)
        self.assertEqual(sorted(table.keys()), ["b", "c"])

    def test_rehash_preserves_all_values(self):
        table = HashMap(2)
        for number in range(100):
            table.put("key:" + str(number), "value:" + str(number))

        self.assertGreaterEqual(table.capacity, 256)
        self.assertEqual(table.size(), 100)
        for number in range(100):
            self.assertEqual(
                table.get("key:" + str(number)),
                "value:" + str(number),
            )

    def test_fnv1a_distribution_example(self):
        """고정된 512개 예시 키가 64개 버킷에 고르게 퍼지는지 확인한다."""
        table = HashMap(64)
        bucket_counts = [0] * 64
        for number in range(512):
            index = table._hash("key:" + str(number)) % 64
            bucket_counts[index] += 1

        used_bucket_count = 0
        for count in bucket_counts:
            if count > 0:
                used_bucket_count += 1
        self.assertEqual(used_bucket_count, 64)
        self.assertLessEqual(max(bucket_counts), 20)


class MinHeapTest(unittest.TestCase):
    def test_heap_order(self):
        heap = MinHeap()
        heap.push((30, "c"))
        heap.push((10, "a"))
        heap.push((20, "b"))
        self.assertEqual(heap.peek(), (10, "a"))
        self.assertEqual(heap.pop(), (10, "a"))
        self.assertEqual(heap.pop(), (20, "b"))
        self.assertEqual(heap.pop(), (30, "c"))
        self.assertIsNone(heap.pop())


if __name__ == "__main__":
    unittest.main()
