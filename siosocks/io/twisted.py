import asyncio
import logging
from asyncio import Future
from typing import List, Optional, Tuple, Union

from twisted.internet.defer import ensureDeferred, Deferred
from twisted.internet.protocol import Protocol
from twisted.internet.interfaces import IStreamClientEndpoint
from twisted.internet.endpoints import connectProtocol

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


def open_connection(
        endpoint: IStreamClientEndpoint,
        host: str,
        port: int,
        socks_version: int,
        username: Optional[Union[bytes, str]] = None,
        password: Optional[Union[bytes, str]] = None,
        encoding: Optional[str] = DEFAULT_ENCODING,
        socks4_extras=None,
        socks5_extras=None,
) -> Deferred[ClientIO]:
    if socks4_extras is None:
        socks4_extras = {}
    if socks5_extras is None:
        socks5_extras = {}

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
    client_io = ClientIO()
    io_deferred = connectProtocol(endpoint, client_io)
    io_deferred.addCallback(ensureDeferred(async_engine(protocol=protocol, io=client_io)))
    return io_deferred

    # await async_engine(protocol=protocol, io=io)
