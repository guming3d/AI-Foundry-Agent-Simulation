import sys

import main


def test_main_defaults_to_tui(monkeypatch):
    called = {"tui": 0}

    def fake_run_tui():
        called["tui"] += 1

    monkeypatch.setattr(main, "run_tui", fake_run_tui)
    monkeypatch.setattr(sys, "argv", ["main.py"])

    main.main()

    assert called["tui"] == 1


def test_main_tui_subcommand_still_works(monkeypatch):
    called = {"tui": 0}

    def fake_run_tui():
        called["tui"] += 1

    monkeypatch.setattr(main, "run_tui", fake_run_tui)
    monkeypatch.setattr(sys, "argv", ["main.py", "tui"])

    main.main()

    assert called["tui"] == 1

