"""Kein Test darf ins Netz: Relic und Discord sind in den Tests durch Fakes
ersetzt. Ein versehentlicher echter Abruf laesst den Test scheitern."""

from __future__ import annotations

import urllib.request

import pytest


@pytest.fixture(autouse=True)
def kein_netz(monkeypatch):
    def blockiert(*_args, **_kwargs):
        raise AssertionError("Test hat versucht, ins Netz zu gehen")

    monkeypatch.setattr(urllib.request, "urlopen", blockiert)
