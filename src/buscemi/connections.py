# http://wbec-ridderkerk.nl/html/UCIProtocol.html

import asyncio
import asyncio.subprocess
import logging
import re
from typing import AsyncIterator, Generator, List, Optional, Pattern, Union


__all__ = [
    "AsyncConnection", "BlockingConnection",
    "read", "read_sync", "read_until", "read_until_sync",
    "write", "write_sync"
]

logger = logging.getLogger(__name__)


async def _new_conn(executable: str) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        executable,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE
    )


def _block(future, *, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()
    return loop.run_until_complete(future)


class AsyncConnection:
    """No input or state validation.  Keep track of what your engine is doing somewhere else."""
    proc: Optional[asyncio.subprocess.Process]

    def __init__(self, proc: asyncio.subprocess.Process) -> None:
        self.proc = proc

    @classmethod
    def from_executable(cls, executable: str, *, loop=None) -> "AsyncConnection":
        proc = _block(_new_conn(executable), loop=loop)
        return cls(proc)

    async def uci(self) -> List[str]:
        await write(self, "uci")
        return [x async for x in read_until(self, "uciok")]

    async def debug(self, enable: bool = True) -> None:
        mode = "on" if enable else "off"
        await write(self, f"debug {mode}")

    async def isready(self) -> List[str]:
        await write(self, "isready")
        return [x async for x in read_until(self, "readyok")]

    async def setoption(self, name: str, value: Optional[str] = None) -> None:
        cmd = f"setoption name {name}"
        if value is not None:
            cmd += f" value {value}"
        await write(self, cmd)

    # NOT SUPPORTED: register

    async def ucinewgame(self) -> None:
        await write(self, "ucinewgame")

    async def position(self, fen: Optional[str] = None, moves: Optional[List[str]] = None) -> None:
        if not (fen or moves):
            raise ValueError("must specify fen or moves")
        if fen:
            cmd = f"position fen {fen}"
        else:
            cmd = f"position startpos moves " + " ".join(moves)
        await write(self, cmd)

    async def go(self, args: List[str]) -> None:
        await write(self, f"go {' '.join(args)}")

    async def stop(self) -> List[str]:
        await write(self, "stop")
        return [x async for x in read_until(self, "bestmove")]

    async def ponderhit(self) -> List[str]:
        await write(self, "ponderhit")
        return [x async for x in read_until(self, "bestmove")]

    async def quit(self) -> None:
        await write(self, "quit")
        await self.proc.wait()
        self.proc = None


async def write(conn: AsyncConnection, data: str, wait: bool = True) -> None:
    if not data.endswith("\n"):
        data += "\n"
    conn.proc.stdin.write(data.encode("ascii"))
    if wait:
        await conn.proc.stdin.drain()
    logger.debug(f">>> {data!r}")


async def read(conn: AsyncConnection) -> AsyncIterator[str]:
    while True:
        line = await conn.proc.stdout.readline()
        line = line.decode("ascii").strip()
        logger.debug(f"<<< {line!r}")
        yield line


async def read_until(conn: AsyncConnection, pattern: Union[str, Pattern]) -> AsyncIterator[str]:
    if isinstance(pattern, str):
        pattern = re.compile(pattern)
    async for line in read(conn):
        yield line
        if pattern.match(line):
            break


class BlockingConnection:
    """No input or state validation.  Keep track of what your engine is doing somewhere else."""
    async_conn: AsyncConnection

    def __init__(self, async_conn: AsyncConnection) -> None:
        self.async_conn = async_conn

    @classmethod
    def from_executable(cls, executable: str) -> "BlockingConnection":
        async_conn = AsyncConnection.from_executable(executable)
        return cls(async_conn)

    def uci(self) -> List[str]:
        return _block(self.async_conn.uci())

    def debug(self, enable: bool = True) -> None:
        return _block(self.async_conn.debug(enable))

    def isready(self) -> List[str]:
        return _block(self.async_conn.isready())

    def setoption(self, name: str, value: Optional[str] = None) -> None:
        return _block(self.async_conn.setoption(name, value))

    # NOT SUPPORTED: register

    def ucinewgame(self) -> None:
        return _block(self.async_conn.ucinewgame())

    def position(self, fen: Optional[str] = None, moves: Optional[List[str]] = None) -> None:
        return _block(self.async_conn.position(fen, moves))

    def go(self, args: List[str]) -> None:
        return _block(self.async_conn.go(args))

    def stop(self) -> List[str]:
        return _block(self.async_conn.stop())

    def ponderhit(self) -> List[str]:
        return _block(self.async_conn.ponderhit())

    def quit(self) -> None:
        _block(self.async_conn.quit())
        self.async_conn = None


def write_sync(conn: Union[AsyncConnection, BlockingConnection], data: str) -> None:
    if isinstance(conn, BlockingConnection):
        conn = conn.async_conn
    _block(write(conn, data, wait=True))


def read_sync(conn: Union[AsyncConnection, BlockingConnection]) -> Generator[str, None, None]:
    if isinstance(conn, BlockingConnection):
        conn = conn.async_conn
    loop = asyncio.get_event_loop()
    reader = read(conn)

    try:
        while True:
            yield loop.run_until_complete(reader.__anext__())
    except StopAsyncIteration:
        pass


def read_until_sync(
        conn: Union[AsyncConnection, BlockingConnection],
        pattern: Union[str, Pattern]) -> Generator[str, None, None]:
    if isinstance(conn, BlockingConnection):
        conn = conn.async_conn
    loop = asyncio.get_event_loop()
    reader = read_until(conn, pattern)

    try:
        while True:
            yield loop.run_until_complete(reader.__anext__())
    except StopAsyncIteration:
        pass
