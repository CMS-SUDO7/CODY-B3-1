"""O(1) 삽입·삭제·이동을 지원하는 이중 연결 리스트."""


class ListNode:
    """이중 연결 리스트의 노드.

    prev와 next는 인접 노드를, data는 사용자가 저장한 값을 가리킨다.
    """

    def __init__(self, data):
        self.prev = None
        self.next = None
        self.data = data


class DoublyLinkedList:
    """head와 tail을 유지하여 양 끝 연산을 O(1)에 처리한다."""

    def __init__(self):
        self.head = None
        self.tail = None
        self.length = 0

    def insert_front(self, data):
        node = ListNode(data)
        if self.head is None:
            self.head = node
            self.tail = node
        else:
            node.next = self.head
            self.head.prev = node
            self.head = node
        self.length += 1
        return node

    def insert_back(self, data):
        node = ListNode(data)
        if self.tail is None:
            self.head = node
            self.tail = node
        else:
            node.prev = self.tail
            self.tail.next = node
            self.tail = node
        self.length += 1
        return node

    def remove_front(self):
        if self.head is None:
            return None
        return self.remove_node(self.head)

    def remove_back(self):
        if self.tail is None:
            return None
        return self.remove_node(self.tail)

    def remove_node(self, node):
        """주어진 노드를 O(1)에 제거하고 저장된 data를 반환한다."""
        if node is None:
            return None

        if node.prev is None:
            self.head = node.next
        else:
            node.prev.next = node.next

        if node.next is None:
            self.tail = node.prev
        else:
            node.next.prev = node.prev

        data = node.data
        node.prev = None
        node.next = None
        self.length -= 1
        return data

    def move_to_front(self, node):
        """이미 리스트에 있는 노드를 새 노드 생성 없이 O(1)에 앞으로 옮긴다."""
        if node is None or node is self.head:
            return node

        if node.prev is not None:
            node.prev.next = node.next
        if node.next is not None:
            node.next.prev = node.prev
        else:
            self.tail = node.prev

        node.prev = None
        node.next = self.head
        self.head.prev = node
        self.head = node
        return node

    def size(self):
        return self.length
