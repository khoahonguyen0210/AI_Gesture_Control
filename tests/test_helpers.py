from __future__ import annotations

import pytest

from gesture_mouse.config import GestureConfig
from gesture_mouse.geometry import Pose, classify_pose
from helpers import both_pinch, make_landmarks

CFG = GestureConfig()


@pytest.mark.parametrize("rotation", [0.0, 0.5])
def test_synthetic_poses_match_their_names(rotation: float) -> None:
    def pose(name: str, ratio: float = 0.05) -> Pose:
        return classify_pose(make_landmarks(name, ratio=ratio, rotation=rotation), CFG)

    point = pose("point")
    assert point.index_ext and not point.middle_ext
    assert point.ratio_ti > CFG.pinch_off

    two = pose("two_finger")
    assert two.index_ext and two.middle_ext and not two.ring_ext and not two.pinky_ext

    left = pose("pinch_left")
    assert left.ratio_ti == pytest.approx(0.05)
    assert left.index_can_pinch and left.ratio_tm > CFG.pinch_off

    right = pose("pinch_right")
    assert right.ratio_tm == pytest.approx(0.05)
    assert right.middle_can_pinch and right.ratio_ti > CFG.pinch_off

    for name in ("open", "point", "two_finger"):
        p = pose(name)
        assert p.ratio_ti > CFG.pinch_off or not p.index_can_pinch
        assert p.ratio_tm > CFG.pinch_off or not p.middle_can_pinch


def test_both_pinch_sets_both_ratios() -> None:
    p = classify_pose(both_pinch(0.1, 0.2).landmarks, CFG)
    assert p.ratio_ti == pytest.approx(0.1)
    assert p.ratio_tm == pytest.approx(0.2)
    assert p.index_can_pinch and p.middle_can_pinch


def test_unknown_pose_rejected() -> None:
    with pytest.raises(ValueError):
        make_landmarks("wave")
