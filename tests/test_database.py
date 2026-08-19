import unittest

from mini_redis.cli import execute_tokens
from mini_redis.database import MiniRedis


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class MiniRedisTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.redis = MiniRedis(clock=self.clock)

    def assert_storage_invariants(self):
        """data, LRU 리스트, lru_nodes, used_memory의 일관성을 검사한다."""
        data_keys = self.redis.data.keys()
        lru_keys = []
        calculated_memory = 0
        current = self.redis.lru.head
        previous = None

        while current is not None:
            self.assertIs(current.prev, previous)
            self.assertTrue(self.redis.data.contains(current.data))
            self.assertIs(self.redis.lru_nodes.get(current.data), current)
            lru_keys.append(current.data)
            previous = current
            current = current.next

        for key in data_keys:
            self.assertEqual(lru_keys.count(key), 1)
            calculated_memory += self.redis._entry_size(key, self.redis.data.get(key))

        self.assertEqual(len(lru_keys), len(data_keys))
        self.assertEqual(self.redis.lru.size(), len(data_keys))
        self.assertEqual(self.redis.lru_nodes.size(), len(data_keys))
        self.assertEqual(self.redis.used_memory, calculated_memory)

    def test_basic_commands_and_utf8_memory(self):
        self.assertEqual(self.redis.set("name", "Alice"), "OK")
        self.assertEqual(self.redis.get("name"), '"Alice"')
        self.assertEqual(self.redis.exists("name"), "(integer) 1")
        self.assertEqual(self.redis.dbsize(), "(integer) 1")
        self.assertEqual(self.redis.used_memory, 9)
        self.assertEqual(self.redis.delete("name"), "(integer) 1")
        self.assertEqual(self.redis.get("name"), "(nil)")

        self.redis.set("한", "글")
        self.assertEqual(self.redis.used_memory, 6)

    def test_ttl_expiration_and_overwrite_reset(self):
        self.redis.set("session", "abc")
        self.assertEqual(self.redis.ttl("session"), "(integer) -1")
        self.assertEqual(self.redis.expire("session", "10"), "(integer) 1")
        self.assertEqual(self.redis.ttl("session"), "(integer) 10")
        self.clock.advance(11)
        self.assertEqual(self.redis.get("session"), "(nil)")
        self.assertEqual(self.redis.ttl("session"), "(integer) -2")

        self.redis.set("k", "v")
        self.redis.expire("k", "5")
        self.redis.set("k", "new")
        self.assertEqual(self.redis.ttl("k"), "(integer) -1")

    def test_expire_edge_cases_and_lazy_deletion(self):
        self.assertEqual(self.redis.expire("missing", "5"), "(integer) 0")
        self.redis.set("a", "1")
        self.redis.expire("a", "10")
        self.redis.expire("a", "20")
        self.clock.advance(11)
        self.assertEqual(self.redis.get("a"), '"1"')
        self.clock.advance(10)
        self.assertEqual(self.redis.get("a"), "(nil)")

        self.redis.set("now", "gone")
        self.assertEqual(self.redis.expire("now", "0"), "(integer) 1")
        self.assertEqual(self.redis.exists("now"), "(integer) 0")

    def test_lru_eviction_and_oom(self):
        self.assertEqual(self.redis.config_set_maxmemory("6"), "OK")
        self.redis.set("a", "11")  # 3 bytes
        self.redis.set("b", "22")  # 3 bytes; a is LRU
        self.redis.get("a")         # b becomes LRU
        self.redis.set("c", "33")  # b is evicted
        self.assertEqual(self.redis.get("b"), "(nil)")
        self.assertEqual(self.redis.get("a"), '"11"')
        self.assertEqual(self.redis.get("c"), '"33"')
        self.assertEqual(self.redis.evicted_keys, 1)
        self.assert_storage_invariants()

        before = self.redis.used_memory
        self.assertEqual(self.redis.set("huge", "123456"), MiniRedis.OOM_ERROR)
        self.assertEqual(self.redis.used_memory, before)
        self.assertEqual(self.redis.get("huge"), "(nil)")
        self.assert_storage_invariants()

    def test_oom_update_preserves_old_value_and_ttl(self):
        self.redis.config_set_maxmemory("8")
        self.redis.set("k", "old")
        self.redis.expire("k", "30")
        self.assertEqual(self.redis.set("k", "12345678"), MiniRedis.OOM_ERROR)
        self.assertEqual(self.redis.get("k"), '"old"')
        self.assertEqual(self.redis.ttl("k"), "(integer) 30")

    def test_config_shrink_keys_and_info(self):
        self.redis.set("a", "11")
        self.redis.set("b", "22")
        self.assertIn('"a"', self.redis.keys())
        self.assertIn('"b"', self.redis.keys())
        self.assertEqual(self.redis.config_set_maxmemory("3"), "OK")
        self.assertEqual(self.redis.dbsize(), "(integer) 1")
        self.assertIn("used_memory:3", self.redis.info_memory())
        self.assertIn("maxmemory:3", self.redis.info_memory())
        self.assertIn("evicted_keys:1", self.redis.info_memory())

        self.assertEqual(self.redis.config_set_maxmemory("-1"), MiniRedis.INTEGER_ERROR)

    def test_info_memory_exact_format(self):
        self.redis.set("name", "Alice")
        self.redis.config_set_maxmemory("100")
        self.assertEqual(
            self.redis.info_memory(),
            "used_memory:9\nmaxmemory:100\nevicted_keys:0",
        )

    def test_expired_get_does_not_touch_lru(self):
        self.redis.set("old", "1")
        self.redis.set("live", "2")
        self.redis.expire("old", "1")
        self.clock.advance(2)
        self.assertEqual(self.redis.get("old"), "(nil)")
        self.assertEqual(self.redis.lru.head.data, "live")
        self.assert_storage_invariants()

    def test_cli_validation_and_quoted_value(self):
        self.assertEqual(execute_tokens(self.redis, ["SET", "greeting", "hello world"]), "OK")
        self.assertEqual(execute_tokens(self.redis, ["GET", "greeting"]), '"hello world"')
        self.assertIn("wrong number", execute_tokens(self.redis, ["GET"]))
        self.assertIn("unknown command", execute_tokens(self.redis, ["NOPE"]))
        self.assertEqual(execute_tokens(self.redis, ["CONFIG", "SET", "maxmemory", "x"]), MiniRedis.INTEGER_ERROR)

    def test_error_prefix_and_exact_formats(self):
        errors = [
            execute_tokens(self.redis, ["GET"]),
            execute_tokens(self.redis, ["NOPE"]),
            execute_tokens(self.redis, ["CONFIG", "GET", "maxmemory", "1"]),
            execute_tokens(self.redis, ["INFO", "stats"]),
            execute_tokens(self.redis, ["EXPIRE", "key", "NaN"]),
        ]
        for error in errors:
            self.assertTrue(error.startswith("(error) "))

        self.assertEqual(
            errors[0],
            "(error) ERR wrong number of arguments for 'get' command",
        )
        self.assertEqual(errors[1], "(error) ERR unknown command 'NOPE'")
        self.assertEqual(errors[4], MiniRedis.INTEGER_ERROR)


if __name__ == "__main__":
    unittest.main()
