"""Fixtures de teste — app Flask com banco temporário."""
from __future__ import annotations

import pytest

from app import create_app
from core.db import Database
from core.seed import executar_seed, SENHA_DEV


@pytest.fixture()
def app(tmp_path):
    db_path = tmp_path / "test.db"
    application = create_app(db_path=db_path)
    application.config.update(
        TESTING=True,
        SECRET_KEY="test",
    )
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    from core.db import get_db

    return get_db()


def login(client, email, senha=SENHA_DEV):
    return client.post(
        "/login",
        data={"email": email, "senha": senha},
        follow_redirects=True,
    )
