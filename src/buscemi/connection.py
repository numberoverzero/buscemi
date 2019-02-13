import asyncio
import asyncio.subprocess
import logging
import re
from typing import AsyncIterator, Iterable, List, Optional, Pattern, Union


__all__ = ["UciConnection", "read", "read_until", "write"]

logger = logging.getLogger(__name__)


class UciConnection:
    """
    No input or state validation.  Keep track of what your engine is doing somewhere else.

    .. seealso::

        http://wbec-ridderkerk.nl/html/UCIProtocol.html
    """
    proc: Optional[asyncio.subprocess.Process]

    def __init__(self, proc: asyncio.subprocess.Process) -> None:
        self.proc = proc

    @classmethod
    async def from_executable(cls, executable: str) -> "UciConnection":
        proc = await asyncio.create_subprocess_exec(
            executable,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE
        )
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

    async def position(self, fen: Optional[str] = None, moves: Optional[Iterable[str]] = None) -> None:
        if fen and moves:
            raise ValueError("must specify only one of fen or moves")
        if fen:
            cmd = f"position fen {fen}"
        else:
            cmd = f"position startpos moves " + " ".join(moves)
        await write(self, cmd)

    async def go(self, args: List[str]) -> None:
        await write(self, f"go {' '.join(args)}")

    async def stop(self) -> None:
        await write(self, "stop")

    async def ponderhit(self) -> None:
        await write(self, "ponderhit")

    async def quit(self) -> None:
        if not self.proc:
            return
        await write(self, "quit")
        await self.proc.wait()
        self.proc = None


async def write(conn: UciConnection, data: str, wait: bool = True) -> None:
    if not data.endswith("\n"):
        data += "\n"
    conn.proc.stdin.write(data.encode("ascii"))
    if wait:
        await conn.proc.stdin.drain()
    logger.debug(f">>> {data!r}")


async def read(conn: UciConnection) -> AsyncIterator[str]:
    readline = conn.proc.stdout.readline
    while True:
        line = await readline()
        line = line.decode("ascii")
        logger.debug(f"<<< {line!r}")
        yield line.strip()


async def read_until(conn: UciConnection, pattern: Union[str, Pattern]) -> AsyncIterator[str]:
    if isinstance(pattern, str):
        pattern = re.compile(pattern)
    async for line in read(conn):
        yield line
        if pattern.match(line):
            break
