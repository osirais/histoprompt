import stat

from histoprompt.setup_config import parse_env, render_env, write_private


def test_render_env_fills_local_values_without_changing_comments():
    template = "# kept\nTOKEN=\nMODE=remote\n"

    rendered = render_env(template, {"TOKEN": "private-value", "MODE": "local"})

    assert rendered == "# kept\nTOKEN=private-value\nMODE=local\n"
    assert parse_env(rendered) == {"TOKEN": "private-value", "MODE": "local"}


def test_write_private_creates_owner_only_file(tmp_path):
    path = tmp_path / ".env.local"

    write_private(path, "TOKEN=private-value\n")

    assert path.read_text() == "TOKEN=private-value\n"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
