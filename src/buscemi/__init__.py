import asyncio
import copy
import functools
import secrets

from . import parsing
from .connection import UciConnection, read
from .models import Position, Search, SearchConfig


__all__ = ["Connection", "Position", "Search", "SearchConfig", "open_connection"]


async def _async_noop():
    pass


# noinspection PyProtectedMember
class Connection:
    def __init__(self, conn: UciConnection):
        self._uci = conn
        self._initialized = False
        self._options = {}
        self._set_options = {}

        self._search: Search = None

    async def __aenter__(self) -> "Connection":
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        if self.is_initialized:
            return
        opts = self._options = {}
        for line in await self._uci.uci():
            opt = parsing.extract_option(line)
            if not opt:
                continue
            opts[opt["name"].lower()] = opt
        self._initialized = True

    async def set_options(self, **options) -> None:
        await self._stop()
        for name, value in options.items():
            opt = self._options[name.lower()]
            name, value = parsing.format_set_option(opt, value)
            await self._uci.setoption(name, value)
        self._set_options.update(options)

    async def search(self, *, position: Position = None, config: SearchConfig = None) -> Search:
        position = position or Position()
        config = config or SearchConfig()

        await self._stop()
        await self._uci.ucinewgame()
        await self._uci.position(fen=position.fen, moves=position.moves)
        await self._uci.isready()
        await self._uci.go(config.render())

        assert self._search is None
        search_id = secrets.token_hex(16)
        search = self._search = Search(
            position=position,
            config=config,
            engine_options=copy.deepcopy(self._set_options),

            _id=search_id,
            _done=asyncio.Event(),
            _progress=asyncio.Event(),
            _stop_func=functools.partial(self._stop, search_id)
        )
        asyncio.create_task(self._run_search(search))
        return self._search

    async def _run_search(self, search: Search) -> None:
        def progress():
            search._progress.set()
            search._progress.clear()

        async for line in read(self._uci):
            if line.startswith("info"):
                search.info.append(line)
                progress()
            elif line.startswith("bestmove"):
                search.bestmove = line
                progress()
                break

        self._search._done.set()

    async def _stop(self, search_id: str = None) -> None:
        await self._uci.stop()

        # nothing running
        if not self._search:
            return
        self._search._was_stopped = True

        # allow None so this class can call _stop() without knowing the current search
        # require search id from Search instances so we don't have a dangling _stop_func
        if search_id and search_id != self._search._id:
            return

        # disconnect Search._stop_func and drain pending info
        self._search._stop_func = _async_noop
        await self._search._done.wait()

        self._search = None

    async def close(self) -> None:
        if not self._uci:
            return
        await self._stop()
        await self._uci.quit()
        self._uci = None


async def open_connection(executable: str) -> Connection:
    uci = await UciConnection.from_executable(executable)
    conn = Connection(uci)
    await conn.initialize()
    return conn
