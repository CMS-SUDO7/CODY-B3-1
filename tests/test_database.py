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

        before = self.redis.used_memory
        self.assertEqual(self.redis.set("huge", "123456"), MiniRedis.OOM_ERROR)
        self.assertEqual(self.redis.used_memory, before)
        self.assertEqual(self.redis.get("huge"), "(nil)")

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

    def test_cli_validation_and_quoted_value(self):
        self.assertEqual(execute_tokens(self.redis, ["SET", "greeting", "hello world"]), "OK")
        self.assertEqual(execute_tokens(self.redis, ["GET", "greeting"]), '"hello world"')
        self.assertIn("wrong number", execute_tokens(self.redis, ["GET"]))
        self.assertIn("unknown command", execute_tokens(self.redis, ["NOPE"]))
        self.assertEqual(execute_tokens(self.redis, ["CONFIG", "SET", "maxmemory", "x"]), MiniRedis.INTEGER_ERROR)


if __name__ == "__main__":
    unittest.main()
