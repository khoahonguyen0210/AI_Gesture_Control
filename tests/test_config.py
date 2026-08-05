from __future__ import annotations

from pathlib import Path

import pytest

from gesture_mouse.__main__ import build_parser, load_from_args, main
from gesture_mouse.config import AppConfig, load_config, validate
from gesture_mouse.errors import ConfigError

DEFAULT_TOML = Path(__file__).resolve().parent.parent / "config" / "default.toml"


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "user.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_u_cfg_01_defaults_are_valid() -> None:
    validate(AppConfig())


def test_u_cfg_02_default_toml_equals_defaults() -> None:
    assert load_config(DEFAULT_TOML) == AppConfig()


def test_u_cfg_03_override_changes_only_given_keys(tmp_path: Path) -> None:
    cfg = load_config(write(tmp_path, "[gesture]\ndrag_hold_ms = 500\n"))
    assert cfg.gesture.drag_hold_ms == 500
    assert cfg.gesture.pinch_on == AppConfig().gesture.pinch_on
    assert cfg.camera == AppConfig().camera


def test_u_cfg_04_unknown_key_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="unknown key gesture.wiggle"):
        load_config(write(tmp_path, "[gesture]\nwiggle = 1\n"))


def test_unknown_section_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="unknown section"):
        load_config(write(tmp_path, "[sound]\nvolume = 1\n"))


def test_wrong_type_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="wrong type"):
        load_config(write(tmp_path, '[camera]\nindex = "zero"\n'))


def test_u_cfg_05_pinch_off_not_above_pinch_on(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="pinch_off must be greater"):
        load_config(write(tmp_path, "[gesture]\npinch_on = 0.3\npinch_off = 0.1\n"))


def test_u_cfg_06_negative_timing_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="drag_hold_ms"):
        load_config(write(tmp_path, "[gesture]\ndrag_hold_ms = -5\n"))


def test_u_cfg_07_margin_without_active_region_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="cursor.margin"):
        load_config(write(tmp_path, "[cursor]\nmargin = 0.5\n"))


@pytest.mark.parametrize("alpha", [0.0, 1.5, -0.1])
def test_u_cfg_08_alpha_out_of_range_rejected(tmp_path: Path, alpha: float) -> None:
    with pytest.raises(ConfigError, match="smoothing_alpha"):
        load_config(write(tmp_path, f"[cursor]\nsmoothing_alpha = {alpha}\n"))


def test_alpha_of_one_allowed(tmp_path: Path) -> None:
    cfg = load_config(write(tmp_path, "[cursor]\nsmoothing_alpha = 1\n"))
    assert cfg.cursor.smoothing_alpha == 1


def test_u_cfg_09_all_errors_reported_together(tmp_path: Path) -> None:
    text = "[gesture]\npinch_off = 0.1\nwiggle = 2\n[cursor]\nmargin = 0.7\n"
    with pytest.raises(ConfigError) as info:
        load_config(write(tmp_path, text))
    assert len(info.value.problems) == 3


def test_u_cfg_10_cli_camera_beats_file(tmp_path: Path) -> None:
    path = write(tmp_path, "[camera]\nindex = 1\n")
    args = build_parser().parse_args(["--config", str(path), "--camera", "2"])
    assert load_from_args(args).camera.index == 2


def test_missing_config_file_exits_with_code_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--config", "does_not_exist.toml"]) == 2
    assert "config file not found" in capsys.readouterr().err


def test_bad_toml_reported(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="cannot read"):
        load_config(write(tmp_path, "[camera\n"))


def test_quit_keys_must_be_single_characters(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="one character"):
        load_config(write(tmp_path, '[control]\nquit_keys = ["quit"]\n'))
