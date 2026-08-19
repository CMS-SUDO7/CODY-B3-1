import unittest

from mini_redis.hash_map import HashMap
from mini_redis.linked_list import DoublyLinkedList
from mini_redis.min_heap import MinHeap


class DoublyLinkedListTest(unittest.TestCase):
    def test_insert_move_and_remove(self):
        linked = DoublyLinkedList()
        first = linked.insert_back("a")
        linked.insert_back("b")
        linked.move_to_front(linked.tail)
        self.assertEqual(linked.head.data, "b")
        self.assertEqual(linked.remove_back(), "a")
        self.assertIsNone(first.prev)
        self.assertEqual(linked.size(), 1)


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
