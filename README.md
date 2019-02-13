# buscemi

provides asyncio interfaces to UCI.


# High-level API

```python3

import asyncio
from buscemi import open_connection, SearchConfig, Position


async def main():
    # https://chess.stackexchange.com/a/12581
    fen = "N7/P3pk1p/3p2p1/r4p2/8/4b2B/4P1KP/1R6 w - - 0 34"

    conn = await open_connection("stockfish")
    await conn.set_options(MultiPV=3)
    search = await conn.search(
        position=Position(fen=fen),
        config=SearchConfig(movetime=30000))

    seen = 0
    while not search.is_done:
        await search.wait_progress()
        for line in search.info[seen:]:
            print(line, flush=True)
        seen = len(search.info)
    print(search.bestmove, flush=True)

    await conn.close()


asyncio.run(main())
```

## Definitions

```
async def open_connection(executable: str) -> Connection
```

```
Connection:
    @classmethod
    async def from_executable(executable: str) -> Connection

    async def initialize()
    async def set_options(**options)
    async def search(
            position: Position=None,
            config: SearchConfig=None) -> Search
    async def close()
```

```
Search:
    position: Position
    config: SearchConfig
    engine_options: Dict[str, Any]

    info: List[str]
    bestmove: str

    is_done: bool
    was_stopped: bool

    async def wait_progress()
    async def wait_done()
    async def stop()
```

```
Position:
    fen: Optional[str]
    moves: Tuple[str, ...]
```

```
SearchConfig:
    searchmoves: Tuple[str, ...] = field(default_factory=tuple)

    wtime:  int = None
    btime:  int = None
    winc:  int = None
    binc:  int = None
    movestogo: int = None

    depth: int = None
    nodes: int = None
    mate: int = None

    movetime: int = None
```

# Low-level API

```python

import asyncio
from buscemi.connection import UciConnection, read


async def main():
    # https://chess.stackexchange.com/a/12581
    fen = "N7/P3pk1p/3p2p1/r4p2/8/4b2B/4P1KP/1R6 w - - 0 34"

    conn = await UciConnection.from_executable("stockfish")

    await conn.uci()
    await conn.setoption("MultiPV", "3")
    await conn.ucinewgame()
    await conn.position(fen=fen)
    await conn.isready()
    await conn.go(["movetime", "30000"])

    async for line in read(conn):
        print(line, flush=True)
        if line.startswith("bestmove"):
            break

    await conn.quit()


asyncio.run(main())
```

## Definitions

```
UciConnection:
    @classmethod
    async def from_executable(executable: str) -> UciConnection

    async def uci() -> List[str]
    async def debug(enable = True)
    async def isready() -> List[str]
    async def setoption(name: str, value: str = None)
    async def ucinewgame()
    async def position(fen: str = None, moves: Iterable[str] = None)
    async def go(args: List[str])
    async def stop()
    async def ponderhit()
    async def quit()
```

```
async def read(conn: UciConnection) -> AsyncIterator[str]
async def read_until(
        conn: UciConnection,
        pattern: Union[str, Pattern]) -> AsyncIterator[str]:
async def write(conn: UciConnection, data: str, wait = True)
```
