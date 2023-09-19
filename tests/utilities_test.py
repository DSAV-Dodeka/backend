import pytest_asyncio
from pytest_mock import MockerFixture

import apiserver.lib.utilities as util
import auth.core.util


@pytest_asyncio.fixture
async def mock_random(mocker: MockerFixture):
    time_patch = mocker.patch("time.time_ns")
    time_patch.return_value = 1642276599151222841
    secrets_patch = mocker.patch("secrets.token_bytes")
    secrets_patch.side_effect = lambda b: bytes.fromhex("8ca96077b3191e3c")


def test_hash_hex(mock_random):
    assert auth.core.util.random_time_hash_hex() == "23d6bccd333b8912d52ba72c1f9621ae"
    assert (
        auth.core.util.random_time_hash_hex(b"someone")
        == "d0e8ffed9e32495eef694b45d7789f1f"
    )
    assert auth.core.util.random_time_hash_hex(
        "someother"
    ) == auth.core.util.random_time_hash_hex(b"someother")


def test_usp_hex():
    test_str = "some😁😁emojis"
    assert util.usp_hex(test_str) == "some~f0~9f~98~81~f0~9f~98~81emojis"
    assert (
        util.usp_hex("ka25kja5kasdf;lkja@@@!!!😂s")
        == "ka25kja5kasdf~3blkja~40~40~40~21~21~21~f0~9f~98~82s"
    )
    assert util.de_usp_hex(util.usp_hex(test_str)) == test_str
    # The bottom looks weird due to RLO character
    test_str_2 = "~858!.̷̨͇̙͇̜̦̤̗̟̫͖͙͚̗̤͇̹̟̦͕͓̱̤̻̠̯͇̯͓̩͈͕̣̙̙͕̻̣̟̲̘͕͇‮̙͇̘͔̜͓̳̳̙̠̖͚̘̙̆̐͂̉́͋̆̃͒̑̉͒̑̽͗́́̾̊̌̊͑̒̾*$*~~f081"  # noqa: PLE2502
    assert util.de_usp_hex(util.usp_hex(test_str_2)) == test_str_2


def test_check_white_space():
    test_str = "  s  \tas f\nabc "
    assert util.strip_edge(test_str) == "s  \tas f\nabc"


def test_check_white_space_unicode():
    test_str = " \nasdf \n\t as\t  "  # noqa: RUF001
    replaced = util.strip_edge(test_str)
    print(replaced)
    assert replaced == "asdf \n\t as"
