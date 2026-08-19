"""명령어 검증과 REPL 인터페이스."""

import shlex

from .database import MiniRedis


def wrong_arguments(command):
    return "(error) ERR wrong number of arguments for '" + command + "' command"


def execute_tokens(database, tokens):
    """토큰 배열을 검증하고 해당 MiniRedis 메서드를 호출한다."""
    if not tokens:
        return None

    command = tokens[0].upper()

    if command == "SET":
        return database.set(tokens[1], tokens[2]) if len(tokens) == 3 else wrong_arguments("set")
    if command == "GET":
        return database.get(tokens[1]) if len(tokens) == 2 else wrong_arguments("get")
    if command == "DEL":
        return database.delete(tokens[1]) if len(tokens) == 2 else wrong_arguments("del")
    if command == "EXISTS":
        return database.exists(tokens[1]) if len(tokens) == 2 else wrong_arguments("exists")
    if command == "DBSIZE":
        return database.dbsize() if len(tokens) == 1 else wrong_arguments("dbsize")
    if command == "KEYS":
        return database.keys() if len(tokens) == 1 else wrong_arguments("keys")
    if command == "EXPIRE":
        return database.expire(tokens[1], tokens[2]) if len(tokens) == 3 else wrong_arguments("expire")
    if command == "TTL":
        return database.ttl(tokens[1]) if len(tokens) == 2 else wrong_arguments("ttl")
    if command == "CONFIG":
        if len(tokens) != 4:
            return wrong_arguments("config")
        if tokens[1].upper() != "SET" or tokens[2].lower() != "maxmemory":
            return "(error) ERR unsupported CONFIG option"
        return database.config_set_maxmemory(tokens[3])
    if command == "INFO":
        if len(tokens) != 2:
            return wrong_arguments("info")
        if tokens[1].lower() != "memory":
            return "(error) ERR unsupported INFO section"
        return database.info_memory()

    return "(error) ERR unknown command '" + tokens[0] + "'"


def run_repl():
    """exit/quit 또는 EOF가 들어올 때까지 명령을 반복 실행한다."""
    database = MiniRedis()
    while True:
        try:
            line = input("mini-redis> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if line.strip().lower() in ("exit", "quit"):
            break
        try:
            tokens = shlex.split(line)
        except ValueError as error:
            print("(error) ERR " + str(error))
            continue

        result = execute_tokens(database, tokens)
        if result is not None:
            print(result)
