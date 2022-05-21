import time

import pytest_asyncio
from pytest_mock import MockerFixture

import dodekaserver.utilities as util


@pytest_asyncio.fixture
async def mock_random(mocker: MockerFixture):
    time_patch = mocker.patch('time.time_ns')
    time_patch.return_value = 1642276599151222841
    secrets_patch = mocker.patch('secrets.token_bytes')
    secrets_patch.side_effect = lambda b: bytes.fromhex("8ca96077b3191e3c")


def test_hash_hex(mock_random):
    assert util.random_time_hash_hex() == "4d5835070d310289643956564b10ec0a0b1dbe1c2daf1da3db1a70740fe9f891"
    assert util.random_time_hash_hex(b"someone") == "260559a02a6903f68cf133d21ce502609884db79e4d8c7df16f4ae9ab8705dc6"
    assert util.random_time_hash_hex("someother") == util.random_time_hash_hex(b"someother")


def test_usp_hex():
    test_str = "some😁😁emojis"
    assert util.usp_hex(test_str) == "some~f0~9f~98~81~f0~9f~98~81emojis"
    assert util.usp_hex("ka25kja5kasdf;lkja@@@!!!😂s") == "ka25kja5kasdf~3blkja~40~40~40~21~21~21~f0~9f~98~82s"
    assert util.de_usp_hex(util.usp_hex(test_str)) == test_str
