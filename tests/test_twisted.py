import asyncio
from asyncio import StreamReader, StreamWriter
from typing import AsyncIterable, Awaitable, Callable, Optional, Tuple

import pytest

from siosocks.exceptions import SocksException
from siosocks.io import twisted
from siosocks.io.asyncio import socks_server_handler

HOST = "127.0.0.1"
MESSAGE = b"socks work!"


async def port_using(
        unused_tcp_port_factory: Callable[[], int],
        handler: Callable[[StreamReader, StreamWriter], Awaitable[None]],
) -> AsyncIterable[int]:
    port = unused_tcp_port_factory()
    server = await asyncio.start_server(
            client_connected_cb=handler,
            host=HOST,
            port=port
    )
    yield port
    server.close()
    await server.wait_closed()


@pytest.fixture
async def endpoint_port(unused_tcp_port_factory: Callable[[], int]) -> AsyncIterable[int]:
    async def handler(reader: StreamReader, writer: StreamWriter):
        data = await reader.read(n=8192)
        writer.write(data=data)
        await writer.drain()
        writer.close()
    
    async for port in port_using(
            unused_tcp_port_factory=unused_tcp_port_factory,
            handler=handler,
    ):
        yield port


@pytest.fixture
async def socks_server_port(unused_tcp_port_factory: Callable[[], int]) -> AsyncIterable[int]:
    async for port in port_using(
            unused_tcp_port_factory=unused_tcp_port_factory,
            handler=socks_server_handler,
    ):
        yield port


async def open_connection(
        port: int,
        socks_host: Optional[str] = None,
        socks_port: Optional[int] = None,
        socks_version: Optional[int] = None,
) -> Tuple[StreamReader, StreamWriter]:
    return await twisted.open_connection(
            host=HOST,
            port=port,
            socks_host=socks_host,
            socks_port=socks_port,
            socks_version=socks_version,
    )


@pytest.mark.asyncio
async def test_connection_direct_success(endpoint_port):
    reader, writer = await open_connection(
            port=endpoint_port,
    )
    writer.write(MESSAGE)
    m = await reader.read(8192)
    assert m == MESSAGE


@pytest.mark.asyncio
async def test_connection_socks_success(endpoint_port, socks_server_port):
    reader, writer = await open_connection(
            port=endpoint_port,
            socks_host=HOST,
            socks_port=socks_server_port,
            socks_version=4,
    )
    writer.write(MESSAGE)
    m = await reader.read(8192)
    assert m == MESSAGE


@pytest.mark.asyncio
async def test_connection_socks_failed(unused_tcp_port: int, socks_server_port: int):
    with pytest.raises(SocksException):
        await open_connection(port=unused_tcp_port, socks_port=socks_server_port)


@pytest.mark.asyncio
async def test_connection_partly_passed_error(endpoint_port: int, socks_server_port: int):
    with pytest.raises(SocksException):
        await open_connection(port=endpoint_port, socks_port=socks_server_port)