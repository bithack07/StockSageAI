"""
Unified FA + TA playbook — Part 3 synthesis from Stock_Analysis_Complete_Note.md.pdf.

High-conviction setup requires fundamental score, Stage 2, checklist pass, and margin of safety.
"""
from __future__ import annotations

from typing import Any

from app.services.fundamental_playbook import FA_HIGH_CONVICTION_MIN, compute_fundamental_playbook
from app.services.technical_playbook import STAGE_ADVANCING, compute_technical_playbook


def compute_unified_playbook(symbol: str) -> dict[str, Any]:
    """Combine fundamental and technical playbooks for agents and API."""
    fundamental = compute_fundamental_playbook(symbol)
    technical = compute_technical_playbook(symbol)

    fa_ok = (fundamental.get("fa_score") or {}).get("high_conviction", False)
    stage2 = (technical.get("weinstein_stage") or {}).get("stage") == STAGE_ADVANCING
    checklist_ok = (technical.get("pre_trade_checklist") or {}).get("trade_allowed", False)
    mos = fundamental.get("graham_analysis", {}).get("margin_of_safety_pct")
    mos_ok = mos is not None and mos >= 20

    layers = {
        "fundamental": fa_ok,
        "weinstein_stage_2": stage2,
        "technical_checklist": checklist_ok,
        "margin_of_safety": mos_ok,
    }
    aligned = sum(1 for v in layers.values() if v)
    high_conviction = aligned >= 3 and fa_ok and stage2

    return {
        "symbol": symbol,
        "fundamental_playbook": fundamental,
        "technical_playbook": technical,
        "synthesis": {
            "layers_aligned": layers,
            "aligned_count": aligned,
            "high_conviction_setup": high_conviction,
            "guidance": (
                "All three layers aligned — highest conviction setup (playbook Part 3)."
                if high_conviction
                else "Wait for FA score ≥35, Stage 2, checklist pass, and margin of safety."
            ),
            "fa_threshold": FA_HIGH_CONVICTION_MIN,
        },
        "reference": "Stock_Analysis_Complete_Note.md.pdf",
    }
