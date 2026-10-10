"""Decision layer: thresholds from config -> GO / WARN / NO-GO with a checklist."""
from __future__ import annotations

from dataclasses import dataclass, field

from .detect import CFG
from .geometry import Measurements

T = CFG["thresholds"]


@dataclass
class Check:
    name: str
    status: str          # pass | warn | fail | skip
    value: str
    confidence: float
    reason: str


@dataclass
class Decision:
    verdict: str                      # GO | WARN | NO-GO | CANNOT ASSESS
    checks: list[Check] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def decide(M: Measurements) -> Decision:
    D = Decision(verdict="CANNOT ASSESS", notes=list(M.notes))
    if M.roll_deg is None and M.overhang_cm is None and M.height_m is None:
        return D

    # roll
    if M.roll_deg is None:
        D.checks.append(Check("Body roll", "skip", "n/a", 0, "edges not found"))
    elif M.roll_conf < T["roll_min_conf"]:
        D.checks.append(Check("Body roll", "skip", f"({abs(M.roll_deg):.1f}°)", M.roll_conf,
                              "low confidence: need a clear side view with wheels visible"))
    else:
        a = abs(M.roll_deg)
        side = "right" if M.roll_deg > 0 else "left"
        if a >= T["roll_fail_deg"]:
            D.checks.append(Check("Body roll", "fail", f"{a:.1f}° {side}", M.roll_conf, f"≥ {T['roll_fail_deg']}° rollover risk"))
        elif a >= T["roll_warn_deg"]:
            D.checks.append(Check("Body roll", "warn", f"{a:.1f}° {side}", M.roll_conf, f"≥ {T['roll_warn_deg']}° check load balance"))
        else:
            D.checks.append(Check("Body roll", "pass", f"{a:.1f}°", M.roll_conf, "level"))

    # overhang
    if M.overhang_cm is None:
        D.checks.append(Check("Overhang", "skip", "n/a", 0, "cargo or scale not found"))
    elif M.overhang_conf < T["overhang_min_conf"] or M.view == "unknown":
        D.checks.append(Check("Overhang", "skip", f"({M.overhang_cm:.0f} cm)", M.overhang_conf, "low confidence: needs a clear side or rear view"))
    else:
        v = M.overhang_cm
        if M.overhang_kind == "side":
            st = "fail" if v >= T["side_overhang_fail_cm"] else "pass"
            D.checks.append(Check("Side overhang", st, f"{v:.0f} cm", M.overhang_conf,
                                  f"limit {T['side_overhang_fail_cm']} cm beyond body"))
        else:
            if v >= T["rear_overhang_fail_cm"]:
                st, why = "fail", f"> {T['rear_overhang_fail_cm']} cm legal max"
            elif v >= T["rear_overhang_warn_cm"]:
                st, why = "warn", f"> {T['rear_overhang_warn_cm']} cm, marking required"
            else:
                st, why = "pass", "within limit"
            D.checks.append(Check("Rear overhang", st, f"{v:.0f} cm", M.overhang_conf, why))

    # height
    if M.height_m is None:
        D.checks.append(Check("Height", "skip", "n/a", 0, "no ground line or scale"))
    elif M.height_conf < T["height_min_conf"] or M.view == "unknown":
        D.checks.append(Check("Height", "skip", f"({M.height_m:.2f} m)", M.height_conf, "low confidence: needs a side or rear view with two wheels found"))
    else:
        lim = T["max_height_m"]; mar = T["height_margin_m"]
        if M.height_m > lim + mar:
            st, why = "fail", f"> {lim} m limit (+{mar} m margin for uncalibrated photo)"
        elif M.height_m > lim:
            st, why = "warn", f"near the {lim} m limit, verify at the gate"
        else:
            st, why = "pass", f"limit {lim} m"
        D.checks.append(Check("Height", st, f"{M.height_m:.2f} m", M.height_conf, why))

    statuses = {c.status for c in D.checks}
    if "fail" in statuses:
        D.verdict = "NO-GO"
    elif "warn" in statuses:
        D.verdict = "WARN"
    elif "pass" in statuses:
        D.verdict = "GO"
    return D
