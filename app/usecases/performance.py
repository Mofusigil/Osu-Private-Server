from __future__ import annotations

import math
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from akatsuki_pp_py import Beatmap
from akatsuki_pp_py import Calculator

from app.constants.mods import Mods

# 添加 Star-Rating-Rebirth 模块路径
sys.path.insert(0, str(Path.cwd() / "Star-Rating-Rebirth"))
try:
    from algorithm import calculate as srr_calculate
    SRR_AVAILABLE = True
except ImportError:
    SRR_AVAILABLE = False


def _get_srr_mod_string(mods: int) -> str:
    """将 osu! mods 转换为 Star-Rating-Rebirth 需要的 mod 字符串"""
    if mods & Mods.DOUBLETIME or mods & Mods.NIGHTCORE:
        return "DT"
    elif mods & Mods.HALFTIME:
        return "HT"
    return "NM"


@dataclass
class ScoreParams:
    mode: int
    mods: int | None = None
    combo: int | None = None

    # caller may pass either acc OR 300/100/50/geki/katu/miss
    # passing both will result in a value error being raised
    acc: float | None = None

    n300: int | None = None
    n100: int | None = None
    n50: int | None = None
    ngeki: int | None = None
    nkatu: int | None = None
    nmiss: int | None = None


class PerformanceRating(TypedDict):
    pp: float
    pp_acc: float | None
    pp_aim: float | None
    pp_speed: float | None
    pp_flashlight: float | None
    effective_miss_count: float | None
    pp_difficulty: float | None


class DifficultyRating(TypedDict):
    stars: float
    aim: float | None
    speed: float | None
    flashlight: float | None
    slider_factor: float | None
    speed_note_count: float | None
    stamina: float | None
    color: float | None
    rhythm: float | None
    peak: float | None


class PerformanceResult(TypedDict):
    performance: PerformanceRating
    difficulty: DifficultyRating


def calculate_performances(
    osu_file_path: str,
    scores: Iterable[ScoreParams],
) -> list[PerformanceResult]:
    """\
    Calculate performance for multiple scores on a single beatmap.

    Typically most useful for mass-recalculation situations.

    TODO: Some level of error handling & returning to caller should be
    implemented here to handle cases where e.g. the beatmap file is invalid
    or there an issue during calculation.
    """
    calc_bmap = Beatmap(path=osu_file_path)

    results: list[PerformanceResult] = []

    for score in scores:
        if score.acc and (
            score.n300 or score.n100 or score.n50 or score.ngeki or score.nkatu
        ):
            raise ValueError(
                "Must not specify accuracy AND 300/100/50/geki/katu. Only one or the other.",
            )

        # rosupp ignores NC and requires DT
        if score.mods is not None:
            if score.mods & Mods.NIGHTCORE:
                score.mods |= Mods.DOUBLETIME

        calculator = Calculator(
            mode=score.mode,
            mods=score.mods or 0,
            combo=score.combo,
            acc=score.acc,
            n300=score.n300,
            n100=score.n100,
            n50=score.n50,
            n_geki=score.ngeki,
            n_katu=score.nkatu,
            n_misses=score.nmiss,
        )
        result = calculator.performance(calc_bmap)

        pp = result.pp
        stars = result.difficulty.stars

        # 对于 mania 模式 (mode == 3)，使用 Star-Rating-Rebirth 计算 SR
        # 并按照 SR 比例缩放 PP
        if score.mode == 3 and SRR_AVAILABLE:
            try:
                mod_str = _get_srr_mod_string(score.mods or 0)
                new_sr = srr_calculate(osu_file_path, mod_str)
                
                if not math.isnan(new_sr) and not math.isinf(new_sr) and new_sr > 0:
                    original_sr = stars
                    if original_sr > 0:
                        # 使用 SR 比例的 2.5 次方缩放 PP
                        sr_ratio = new_sr / original_sr
                        pp = pp * (sr_ratio ** 2.5)
                    stars = new_sr
            except Exception:
                # 如果 Star-Rating-Rebirth 计算失败，保持原有值
                pass

        if math.isnan(pp) or math.isinf(pp):
            # TODO: report to logserver
            pp = 0.0
        else:
            pp = round(pp, 3)

        results.append(
            {
                "performance": {
                    "pp": pp,
                    "pp_acc": result.pp_acc,
                    "pp_aim": result.pp_aim,
                    "pp_speed": result.pp_speed,
                    "pp_flashlight": result.pp_flashlight,
                    "effective_miss_count": result.effective_miss_count,
                    "pp_difficulty": result.pp_difficulty,
                },
                "difficulty": {
                    "stars": stars,
                    "aim": result.difficulty.aim,
                    "speed": result.difficulty.speed,
                    "flashlight": result.difficulty.flashlight,
                    "slider_factor": result.difficulty.slider_factor,
                    "speed_note_count": result.difficulty.speed_note_count,
                    "stamina": result.difficulty.stamina,
                    "color": result.difficulty.color,
                    "rhythm": result.difficulty.rhythm,
                    "peak": result.difficulty.peak,
                },
            },
        )

    return results
