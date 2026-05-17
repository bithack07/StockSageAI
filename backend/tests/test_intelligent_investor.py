"""Tests for Graham / Intelligent Investor formulas."""
import math

from app.services.intelligent_investor import (
    graham_number,
    margin_of_safety_pct,
    ncav_per_share,
    pe_times_pb,
    graham_fundamental_verdict,
)


def test_graham_number():
    # EPS=10, BVPS=20 → √(22.5*10*20) = √4500 ≈ 67.08
    g = graham_number(10.0, 20.0)
    assert g is not None
    assert abs(g - math.sqrt(4500)) < 0.1


def test_margin_of_safety():
    mos = margin_of_safety_pct(100.0, 67.0)
    assert mos is not None
    assert mos > 30


def test_pe_times_pb():
    assert pe_times_pb(15, 1.5) == 22.5


def test_ncav():
    ncav = ncav_per_share(1000, 800, 100)
    assert ncav == 2.0


def test_verdict_undervalued():
    v = graham_fundamental_verdict(price=50, gnum=100, mos=50, pe=10, pb=1, pe_pb=10, graham_score=75)
    assert v == "UNDERVALUED"
