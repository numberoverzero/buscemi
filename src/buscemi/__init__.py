import asyncio

from . import parsing
from .connection import _UciConnection, _read
from .models import Position, Search, SearchConfig





__all__ = ["Connection", "Position", "Search", "SearchConfig", "open_uci_connection"]


# noinspection PyProtectedMember
class Connection:
    def __init__(self, conn: _UciConnection):
        self._conn = conn
        self._initialized = False
        self._options = {}

        self._search: Search = None

    async def __aenter__(self):
        await self.initialize()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        if self.is_initialized:
            return
        opts = self._options = {}
        for line in await self._conn.uci():
            opt = parsing.extract_option(line)
            if not opt:
                continue
            opts[opt["name"].lower()] = opt
        self._initialized = True

    async def set_options(self, **options) -> None:
        for name, value in options.items():
            opt = self._options[name.lower()]
            name, value = parsing.format_set_option(opt, value)
            await self._conn.setoption(name, value)

    async def search(self, *, pos: Position = None, config: SearchConfig = None, engine_config: dict = None) -> Search:
        pos = pos or Position()
        config = config or SearchConfig()

        await self.stop()
        await self.set_options(**engine_config)
        await self._conn.ucinewgame()
        await self._conn.position(fen=pos.fen, moves=pos.moves)
        await self._conn.isready()
        await self._conn.go(config.render())

        assert self._search is None
        search = self._search = Search(
            pos=pos,
            config=config,
            engine_config=engine_config,

            _done=asyncio.Event(),
            _progress=asyncio.Event(),
            _stop_func=self.stop
        )
        asyncio.create_task(self._run_search(search))
        return self._search

    async def stop(self) -> None:
        await self._conn.stop()
        if not self._search:
            return
        await self._search._done.wait()
        self._search = None

    async def close(self) -> None:
        if not self._conn:
            return
        await self.stop()
        await self._conn.quit()
        self._conn = None

    async def _run_search(self, search: Search) -> None:
        def toggle_status():
            search._progress.set()
            search._progress.clear()

        async for line in _read(self._conn, timeout=0.5):
            if line.startswith("info"):
                search.info.append(line)
                toggle_status()
            elif line.startswith("bestmove"):
                search.bestmove = line
                toggle_status()
                break

        self._search._done.set()


async def open_uci_connection(executable: str) -> Connection:
    conn = await _UciConnection.from_executable(executable)
    engine = Connection(conn)
    await engine.initialize()
    return engine
