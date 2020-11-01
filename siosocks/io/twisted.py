import asyncio
import logging
from asyncio import Future, StreamReader, StreamWriter
from typing import List, Optional, Tuple, Union

from twisted.internet.protocol import Protocol

from .const import DEFAULT_BLOCK_SIZE
from ..exceptions import SocksException
from ..interface import AbstractSocksIO, async_engine
from ..protocol import DEFAULT_ENCODING, SocksClient

logger = logging.getLogger(__name__)


class ClientIO(Protocol, AbstractSocksIO):
    
    chunks: List[bytes]
    future: Future[None]
    
    def __init__(self):
        self.chunks = []
        self.future = asyncio.get_running_loop().create_future()

    def dataReceived(self, data: bytes):
        self.chunks.append(data)
        if self.future.done():
            return
        self.future.set_result(None)
        self.future = asyncio.get_running_loop().create_future()

    async def read(self) -> bytes:
        if not self.chunks:
            await self.future
        data = b"".join(self.chunks)
        self.chunks.clear()
        return data
    
    async def write(self, data: bytes):
        self.transport.write(data)
    
    async def connect(self, host: int, port: int):
        raise RuntimeError("ClientIO.connect should not be called")
    
    async def passthrough(self):
        return


async def open_connection(
        host: str,
        port: int,
        socks_host: Optional[str] = None,
        socks_port: Optional[int] = None,
        socks_version: Optional[int] = None,
        username: Optional[Union[bytes, str]] = None,
        password: Optional[Union[bytes, str]] = None,
        encoding: Optional[str] = DEFAULT_ENCODING,
        socks4_extras=None,
        socks5_extras=None,
        **open_connection_extras,
) -> Tuple[StreamReader, StreamWriter]:
    if socks4_extras is None:
        socks4_extras = {}
    if socks5_extras is None:
        socks5_extras = {}
    socks_required = socks_host, socks_port, socks_version
    socks_enabled = all(socks_required)
    socks_disabled = not any(socks_required)
    if socks_enabled == socks_disabled:
        raise SocksException("Partly passed socks required arguments: "
                             "socks_host = {!r}, socks_port = {!r}, socks_version = {!r}".format(*socks_required))
    if socks_enabled:
        reader, writer = await asyncio.open_connection(
                host=socks_host,
                port=socks_port,
                **open_connection_extras,
        )
        protocol = SocksClient(
                host=host,
                port=port,
                version=socks_version,
                username=username,
                password=password,
                encoding=encoding,
                socks4_extras=socks4_extras,
                socks5_extras=socks5_extras,
        )
        io = ClientIO(reader=reader, writer=writer)
        await async_engine(protocol=protocol, io=io)
    else:
        reader, writer = await asyncio.open_connection(host=host, port=port, **open_connection_extras)
    return reader, writer
