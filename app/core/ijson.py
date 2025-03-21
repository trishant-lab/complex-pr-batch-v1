import orjson


def ijson_loads(data: bytes | bytearray | memoryview | str) -> dict:
    """
    Helper func to load json data
    """
    return orjson.loads(data)


def ijson_dumps(data: object, option: int | None = None, encoding: str = "utf-8") -> str:
    """
    Helper func to dump json data
    """
    return orjson.dumps(data, option).decode(encoding=encoding)
