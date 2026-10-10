"""Geometry stage: everything is measured relative to objects in the same image,
so camera roll cancels and no absolute camera pose is needed.

roll      = angle(body top edge) - angle(wheel contact line / body bottom edge)
overhang  = cargo extent beyond the truck body, scaled by a known object
height    = cargo top to ground, scaled by a known object
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from .detect import CFG, Box, Detections


@dataclass
class Line:
    x1: float; y1: float; x2: float; y2: float
    @property
    def angle_deg(self):
        return float(np.degrees(np.arctan2(self.y2 - self.y1, self.x2 - self.x1)))
    def as_int(self):
        return int(self.x1), int(self.y1), int(self.x2), int(self.y2)


@dataclass
class Measurements:
    view: str = "unknown"                 # side | rear | unknown
    scale_m_per_px: float | None = None
    scale_source: str = "none"
    roll_deg: float | None = None
    roll_conf: float = 0.0
    top_line: Line | None = None
    bottom_line: Line | None = None
    overhang_cm: float | None = None      # rear overhang in side view, side overhang in rear view
    overhang_kind: str = "none"
    overhang_conf: float = 0.0
    overhang_px: tuple | None = None      # (x_body_edge, x_cargo_edge, y) for drawing
    height_m: float | None = None
    height_conf: float = 0.0
    height_px: tuple | None = None        # (x, y_top, y_ground)
    notes: list[str] = field(default_factory=list)


def _fit_line_ransac(pts: np.ndarray, iters=200, tol=3.0):
    """Robust 2-point line fit on Nx2 points; returns (slope, intercept, inlier_frac)."""
    if len(pts) < 10:
        return None
    rng = np.random.default_rng(0)
    best, best_n = None, 0
    for _ in range(iters):
        i, j = rng.choice(len(pts), 2, replace=False)
        (x1, y1), (x2, y2) = pts[i], pts[j]
        if abs(x2 - x1) < 1e-6:
            continue
        m = (y2 - y1) / (x2 - x1)
        c = y1 - m * x1
        d = np.abs(pts[:, 1] - (m * pts[:, 0] + c))
        n = int((d < tol).sum())
        if n > best_n:
            best_n, best = n, (m, c)
    if best is None:
        return None
    m, c = best
    inl = pts[np.abs(pts[:, 1] - (m * pts[:, 0] + c)) < tol]
    m, c = np.polyfit(inl[:, 0], inl[:, 1], 1)
    return float(m), float(c), best_n / len(pts)


def _edge_points(mask: np.ndarray, top: bool, x_lo: int, x_hi: int):
    cols = np.arange(x_lo, x_hi)
    pts = []
    for x in cols:
        ys = np.flatnonzero(mask[:, x])
        if len(ys):
            pts.append((x, ys.min() if top else ys.max()))
    return np.array(pts, dtype=float)


def measure(det: Detections, img_shape) -> Measurements:
    M = Measurements()
    H, W = img_shape[:2]
    tb = det.truck_box
    if tb is None:
        M.notes.append("no truck found")
        return M
    if tb.w < CFG["thresholds"]["min_truck_box_frac"] * W:
        M.notes.append("truck too small in frame")
        return M

    ar = tb.w / max(tb.h, 1)
    M.view = "side" if ar > 1.6 else ("rear" if ar < 1.25 else "unknown")

    wheels = [b for b in det.by_label("wheel") if tb.xyxy[0] - 10 <= b.cx <= tb.xyxy[2] + 10]
    # ---- scale ----
    if M.view == "rear" and det.truck_mask is not None:
        ys = tb.xyxy[1] + int(tb.h * 0.5)
        xs = np.flatnonzero(det.truck_mask[ys])
        if len(xs) > 10:
            M.scale_m_per_px = CFG["scale"]["trailer_width_m"] / float(xs.max() - xs.min())
            M.scale_source = "body width 2.55 m"
    if M.scale_m_per_px is None and wheels:
        wh = float(np.median([w.h for w in wheels]))
        if wh > 5:
            M.scale_m_per_px = CFG["scale"]["wheel_diameter_m"] / wh
            M.scale_source = "wheel diameter 1.05 m"

    # ---- roll ----
    x_lo = tb.xyxy[0] + int(tb.w * 0.15)
    x_hi = tb.xyxy[2] - int(tb.w * 0.15)
    if det.truck_mask is not None and x_hi - x_lo > 20:
        top = _fit_line_ransac(_edge_points(det.truck_mask, True, x_lo, x_hi))
        bot = None
        if len(wheels) >= 2:
            pts = np.array([(w.cx, w.bottom) for w in wheels], dtype=float)
            m, c = np.polyfit(pts[:, 0], pts[:, 1], 1)
            bot = (float(m), float(c), 1.0)
            bot_src = "wheel contact line"
        else:
            bot = _fit_line_ransac(_edge_points(det.truck_mask, False, x_lo, x_hi))
            bot_src = "body bottom edge"
        if top and bot:
            M.top_line = Line(x_lo, top[0] * x_lo + top[1], x_hi, top[0] * x_hi + top[1])
            M.bottom_line = Line(x_lo, bot[0] * x_lo + bot[1], x_hi, bot[0] * x_hi + bot[1])
            M.roll_deg = M.top_line.angle_deg - M.bottom_line.angle_deg
            M.roll_conf = round(min(top[2], bot[2]) * (1.0 if M.view == "side" else 0.6), 2)
            M.notes.append(f"roll from body top edge vs {bot_src}")
        else:
            M.notes.append("roll: could not fit body edges")
    else:
        M.notes.append("roll: no truck mask")

    # ---- overhang ----
    cargo = [b for b in det.by_label("cargo", "container", "tarpaulin")
             if b.cx > tb.xyxy[0] - tb.w * 0.3 and b.cx < tb.xyxy[2] + tb.w * 0.3]
    if cargo and det.truck_mask is not None:
        big = max(cargo, key=lambda b: b.w * b.h)
        y = int(np.clip((big.xyxy[1] + big.xyxy[3]) / 2, 0, H - 1))
        xs = np.flatnonzero(det.truck_mask[y])
        if len(xs) > 10:
            body_l, body_r = int(xs.min()), int(xs.max())
            over_l = body_l - big.xyxy[0]
            over_r = big.xyxy[2] - body_r
            over_px = max(over_l, over_r, 0)
            if M.scale_m_per_px:
                if over_px == over_l and over_l > 0:
                    M.overhang_px = (body_l, big.xyxy[0], y)
                elif over_r > 0:
                    M.overhang_px = (body_r, big.xyxy[2], y)
                M.overhang_cm = round(over_px * M.scale_m_per_px * 100, 1)
                M.overhang_kind = "rear" if M.view == "side" else "side"
                M.overhang_conf = round(big.conf * (0.9 if M.view != "unknown" else 0.5), 2)
            else:
                M.notes.append("overhang: no scale object (wheel/body) found")
        else:
            M.notes.append("overhang: body edge not found at cargo height")
    else:
        M.notes.append("overhang: no cargo detected")

    # ---- height ----
    ground_y = None
    if wheels:
        ground_y = float(np.median([w.bottom for w in wheels]))
    elif M.bottom_line is not None:
        ground_y = (M.bottom_line.y1 + M.bottom_line.y2) / 2
    top_y = None
    if cargo:
        top_y = min(min(b.xyxy[1] for b in cargo), tb.xyxy[1])
    elif det.truck_mask is not None:
        ys = np.flatnonzero(det.truck_mask.any(axis=1))
        top_y = float(ys.min()) if len(ys) else None
    if ground_y and top_y is not None and M.scale_m_per_px:
        M.height_m = round((ground_y - top_y) * M.scale_m_per_px, 2)
        M.height_conf = round(0.8 if wheels else 0.4, 2)
        M.height_px = (int(tb.cx), int(top_y), int(ground_y))
    else:
        M.notes.append("height: missing ground line or scale")
    return M
