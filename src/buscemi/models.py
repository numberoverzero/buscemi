import asyncio
import dataclasses
from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional, Tuple

from .parsing import format_go_arguments


@dataclass
class SearchConfig:
    searchmoves: Tuple[str, ...] = field(default_factory=tuple)

    wtime:  Optional[int] = None
    btime:  Optional[int] = None
    winc:  Optional[int] = None
    binc:  Optional[int] = None

    movestogo: Optional[int] = None

    depth: Optional[int] = None
    nodes: Optional[int] = None
    mate: Optional[int] = None

    movetime: Optional[int] = None

    def render(self) -> List[str]:
        return format_go_arguments(**dataclasses.asdict(self))


@dataclass
class Position:
    fen: Optional[str] = None
    moves: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.fen and self.moves:
            raise ValueError("must specify one of fen or moves")


@dataclass
class Search:
    _id: str
    _done: asyncio.Event
    _progress: asyncio.Event
    _stop_func: Callable[[], Awaitable]

    position: Position
    config: SearchConfig
    engine_options: dict = field(default_factory=dict, compare=False)

    info: List[str] = field(default_factory=list)
    bestmove: Optional[str] = None

    _was_stopped: bool = False

    async def stop(self) -> None:
        if self.is_done:
            return
        await self._stop_func()
        self._was_stopped = True

    @property
    def is_done(self):
        return self._done.is_set()

    @property
    def was_stopped(self) -> bool:
        """May have terminated the search early"""
        return self._was_stopped

    async def wait_progress(self):
        await self._progress.wait()

    async def wait_done(self):
        await self._done.wait()
