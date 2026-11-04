import json

import pytest

from backend import config
from backend.auth import PASSWORDS, authenticate


@pytest.mark.parametrize('existing', [False, True])
def test_demo_admin_on_fresh_and_existing_install(tmp_path, monkeypatch, existing):
    monkeypatch.setattr(config, 'ROOT', tmp_path)
    for name in ['FLEETFLOW_JWT_SECRET', 'FLEETFLOW_USERS_PATH', 'FLEETFLOW_AUDIT_PATH']:
        monkeypatch.delenv(name, raising=False)
    data = tmp_path / 'data'
    if existing:
        data.mkdir()
        original = {'manager': {'role': 'manager', 'password_hash': PASSWORDS.hash('existing-password')}}
        (data / 'users.json').write_text(json.dumps(original), encoding='utf-8')
        (data / 'jwt.key').write_text('existing-signing-key-' * 3, encoding='utf-8')
        (data / 'LOCAL_ACCOUNTS.txt').write_text('manager: existing-password\n', encoding='utf-8')
    config.configure()
    users = json.loads((data / 'users.json').read_text(encoding='utf-8'))
    assert users['admin']['password_hash'] != '123123'
    assert authenticate('admin', '123123')['role'] == 'manager'
    if existing:
        assert users['manager'] == original['manager']
        assert (data / 'jwt.key').read_text(encoding='utf-8') == 'existing-signing-key-' * 3
    before = {name: (data / name).read_bytes() for name in ['users.json', 'jwt.key', 'LOCAL_ACCOUNTS.txt']}
    config.configure()
    assert all((data / name).read_bytes() == value for name, value in before.items())
