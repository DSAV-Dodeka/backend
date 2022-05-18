import asyncio

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from httpx import AsyncClient

from dodekaserver.db.ops import DbOperations
from dodekaserver.define.entities import SavedRefreshToken, SymmetricKey


@pytest.fixture(scope="module")
def event_loop():
    """ Necessary for async tests with module-scoped fixtures """
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def app_mod():
    import dodekaserver.app as app_mod

    yield app_mod


@pytest_asyncio.fixture(scope="module")
async def app(app_mod):
    # startup, shutdown is not run
    app = app_mod.app
    yield app


@pytest_asyncio.fixture(scope="module", autouse=True)
async def mock_dsrc(app_mod, module_mocker: MockerFixture):
    app_mod.dsrc.gateway = module_mocker.MagicMock(spec=app_mod.dsrc.gateway)
    app_mod.dsrc.gateway.ops = module_mocker.MagicMock(spec=DbOperations)
    yield app_mod.dsrc


@pytest_asyncio.fixture(scope="module")
async def test_client(app):
    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_root(test_client):
    response = await test_client.get("/")

    assert response.status_code == 200
    assert response.json() == {"Hallo": "Atleten"}


@pytest_asyncio.fixture
async def mock_get_keys(module_mocker: MockerFixture):
    mock_symm_key = {
        'id': 2, 'algorithm': 'symmetric', 'public': None, 'private': '8T3oEm_haJZbn6xu-klttJXk5QBPYlurQrqA5SDx-Ck',
        'public_format': None, 'public_encoding': None, 'private_format': 'none', 'private_encoding': 'base64url'
    }
    mock_token_key = {
        'id': 1, 'algorithm': 'ed448',
        'public': '-----BEGIN PUBLIC KEY-----\nMEMwBQYDK2VxAzoAtPGddEupA3b5P5yr9gT3rvjzWeQH5cedY6RcwN3A5zTS9n8C\nc6dOR+'
                  'XUPVLVu0o0i/t46fW1HMQA\n-----END PUBLIC KEY-----\n',
        'private': '-----BEGIN PRIVATE KEY-----\nMEcCAQAwBQYDK2VxBDsEOY1wa98ZvsK8pYML+ICD9Mbtavr+QC5PC301oVn5jPM6\nT8tE'
                   'CKaZvu5mxG/OfxlEKxl/XIKuClP1mw==\n-----END PRIVATE KEY-----\n',
        'public_format': 'X509PKCS#1', 'public_encoding': 'PEM', 'private_format': 'PKCS#8', 'private_encoding': 'PEM'
    }

    get_k_s = module_mocker.patch('dodekaserver.data.key.get_refresh_symmetric')
    get_k_s.return_value = mock_symm_key['private']
    get_k_p = module_mocker.patch('dodekaserver.data.key.get_token_private')
    get_k_p.return_value = mock_token_key['private']


@pytest.mark.asyncio
async def test_refresh(test_client, mock_dsrc, module_mocker: MockerFixture, mock_get_keys):
    import dodekaserver.auth.tokens as tkns

    get_r = module_mocker.patch('dodekaserver.data.refreshtoken.get_refresh_by_id')

    def side_effect(dsrc, id_int):
        return SavedRefreshToken(family_id="", access_value="", id_token_value="", iat=2, exp=2, nonce="")
    get_r.side_effect = side_effect

    a, _ = await tkns.do_refresh(mock_dsrc, "abc")
    assert a == ""