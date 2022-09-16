import pytest_asyncio
from pytest_mock import MockerFixture

import apiserver.utilities as util


@pytest_asyncio.fixture
async def mock_random(mocker: MockerFixture):
    time_patch = mocker.patch('time.time_ns')
    time_patch.return_value = 1642276599151222841
    secrets_patch = mocker.patch('secrets.token_bytes')
    secrets_patch.side_effect = lambda b: bytes.fromhex("8ca96077b3191e3c")


def test_hash_hex(mock_random):
    assert util.random_time_hash_hex() == "23d6bccd333b8912d52ba72c1f9621ae"
    assert util.random_time_hash_hex(b"someone") == "d0e8ffed9e32495eef694b45d7789f1f"
    assert util.random_time_hash_hex("someother") == util.random_time_hash_hex(b"someother")


def test_usp_hex():
    test_str = "some😁😁emojis"
    assert util.usp_hex(test_str) == "some~f0~9f~98~81~f0~9f~98~81emojis"
    assert util.usp_hex("ka25kja5kasdf;lkja@@@!!!😂s") == "ka25kja5kasdf~3blkja~40~40~40~21~21~21~f0~9f~98~82s"
    assert util.de_usp_hex(util.usp_hex(test_str)) == test_str
