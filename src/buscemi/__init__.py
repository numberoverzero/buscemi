from typing import Any, Dict

from . import connections, parsing


__all__ = [
    "Engine",
    "connections"
]


class Engine:
    conn: connections.AsyncConnection
    _cached_opts: dict

    def __init__(self, conn: connections.AsyncConnection) -> None:
        self.conn = conn
        self._cached_opts = {}

    @classmethod
    async def from_executable(cls, executable: str) -> "Engine":
        conn = await connections.AsyncConnection.from_executable(executable)
        return cls(conn)

    async def get_options(self) -> Dict[str, dict]:
        opts = self._cached_opts
        if not opts:
            for line in await self.conn.uci():
                opt = parsing.extract_option(line)
                if not opt:
                    continue
                opts[opt["name"].lower()] = opt
        return opts

    async def set_option(self, name: str, value: Any=parsing.missing):
        options = await self.get_options()
        opt = options[name.lower()]
        name, value = parsing.format_set_option(opt, value)
        await self.conn.setoption(name, value)

    async def close(self) -> None:
        await self.conn.quit()
        self.conn = None
