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
from .wheels import find_wheels, ground_points, body_vertical, scene_vertical


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
    struct_lines: list = field(default_factory=list)
    ref_lines: list = field(default_factory=list)
    roll_reference: str = "none"
    body_vs_camera_deg: float | None = None   # raw instrument reading: body verticals vs image vertical
    bottom_line: Line | None = None
    overhang_cm: float | None = None      # rear overhang in side view, side overhang in rear view
    overhang_kind: str = "none"
    overhang_conf: float = 0.0
    overhang_px: tuple | None = None      # (x_body_edge, x_cargo_edge, y) for drawing
    height_m: float | None = None
    height_conf: float = 0.0
    height_px: tuple | None = None        # (x, y_top, y_ground)
    load_lean_deg: float | None = None    # stacked load above the body: mean lean of its two side edges, + = left
    load_spread_deg: float | None = None  # left edge angle minus right edge angle: + = wider at the top
    load_conf: float = 0.0
    load_lines: list = field(default_factory=list)
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


def measure(det: Detections, img_shape, img: np.ndarray | None = None) -> Measurements:
    M = Measurements()
    H, W = img_shape[:2]
    tb = det.truck_box
    if tb is None:
        M.notes.append("no truck found")
        return M
    if tb.w < CFG["thresholds"]["min_truck_box_frac"] * W:
        M.notes.append("truck too small in frame")
        return M

    # The COCO truck mask often includes a tall load, which makes the box square and the view "rear".
    # The open-vocabulary "truck" box is the vehicle itself: use it for the view, the wheel search and the
    # body width; keep the full box/mask for the load top.
    veh = tb
    for b in sorted(det.by_label("truck"), key=lambda b: -b.conf):
        ix = max(0, min(b.xyxy[2], tb.xyxy[2]) - max(b.xyxy[0], tb.xyxy[0]))
        iy = max(0, min(b.xyxy[3], tb.xyxy[3]) - max(b.xyxy[1], tb.xyxy[1]))
        inside = ix * iy / max(1, b.w * b.h)
        if inside >= 0.8 and b.w >= 0.6 * tb.w and b.h < 0.9 * tb.h and b.h >= 0.25 * tb.h:
            veh = b
            M.notes.append("vehicle box from detector, load above it")
            break
    ar = veh.w / max(veh.h, 1)
    M.view = "side" if ar > 1.6 else ("rear" if ar < 1.25 else "unknown")
    if tb.w / max(tb.h, 1) < 0.9:
        M.view = "rear"          # a whole rig taller than wide is never a side view; the load may hide the body shape

    wheels = [b for b in det.by_label("wheel") if tb.xyxy[0] - 10 <= b.cx <= tb.xyxy[2] + 10]
    if len(wheels) < 2 and det.truck_mask is not None and img is not None:
        found = find_wheels(img, det.truck_mask, veh)
        # drop circles that belong to cars carried on the deck (their wheels are smaller and higher)
        cars = det.by_label("car")
        found = [w for w in found if not any(c.xyxy[0] <= w.cx <= c.xyxy[2] and c.xyxy[1] <= (w.xyxy[1] + w.xyxy[3]) / 2 <= c.xyxy[3] and c.h < 0.8 * tb.h for c in cars)]
        if len(found) >= 2:
            wheels = found
            det.boxes.extend(found)          # so they are drawn and reported
            M.notes.append(f"wheels from circle finder ({len(found)})")
    # ---- scale ----
    if M.view == "rear" and det.truck_mask is not None:
        ys = veh.xyxy[1] + int(veh.h * 0.5)
        xs = np.flatnonzero(det.truck_mask[ys])
        if len(xs) > 10:
            M.scale_m_per_px = CFG["scale"]["trailer_width_m"] / float(xs.max() - xs.min())
            M.scale_source = "body width 2.55 m"
    if M.scale_m_per_px is None and wheels:
        wh = float(np.median([w.h for w in wheels]))
        if wh > 5:
            M.scale_m_per_px = CFG["scale"]["wheel_diameter_m"] / wh
            M.scale_source = "wheel diameter 1.05 m"

    # ---- ground line (for scale / height drawing) ----
    x_lo = tb.xyxy[0] + int(tb.w * 0.15)
    x_hi = tb.xyxy[2] - int(tb.w * 0.15)
    if det.truck_mask is not None and x_hi - x_lo > 20:
        if len(wheels) >= 2:
            pts = np.array([(w.cx, w.bottom) for w in wheels], dtype=float)
            m, c = np.polyfit(pts[:, 0], pts[:, 1], 1)
            M.bottom_line = Line(x_lo, m * x_lo + c, x_hi, m * x_hi + c)
        else:
            gp = ground_points(det.truck_mask, x_lo, x_hi, tb.h)
            if gp is not None and (gp[:, 0].max() - gp[:, 0].min()) > 0.35 * tb.w:
                m, c = np.polyfit(gp[:, 0], gp[:, 1], 1)
                M.bottom_line = Line(x_lo, m * x_lo + c, x_hi, m * x_hi + c)

    # ---- roll: body vertical edges vs a gravity reference in the same image ----
    # Horizontal edges converge under perspective, so a level truck looks tilted when top and bottom
    # edges are compared. Vertical edges on the left and right halves converge in opposite directions,
    # so their mean cancels perspective. The reference is scene verticals (poles, walls) when present,
    # otherwise the camera vertical with reduced confidence.
    if det.truck_mask is not None and img is not None:
        bv = body_vertical(img, det.truck_mask, tb)
        if bv is None or bv[1] < 0.15:
            M.notes.append("roll: no vertical body edges found")
        else:
            sv = scene_vertical(img, det.truck_mask)
            M.struct_lines = bv[2]
            M.body_vs_camera_deg = float(bv[0])
            if sv is not None and sv[1] >= 0.3:
                M.roll_deg = bv[0] - sv[0]
                M.roll_conf = round(min(bv[1], sv[1]) * (1.0 if M.view != "unknown" else 0.7), 2)
                M.ref_lines = sv[2]
                M.roll_reference = "scene verticals"
            else:
                M.roll_deg = bv[0]
                M.roll_conf = round(bv[1] * 0.7 * (1.0 if M.view != "unknown" else 0.7), 2)
                M.roll_reference = "camera vertical"
            M.notes.append(f"roll from body vertical edges vs {M.roll_reference}")
    else:
        M.notes.append("roll: no truck mask")

    # ---- overhang ----
    def _on_truck(b):
        inside_x = tb.xyxy[0] - 0.05 * tb.w <= b.cx <= tb.xyxy[2] + 0.05 * tb.w
        bottom_ok = b.bottom <= tb.xyxy[3] + 0.05 * tb.h          # not a car parked in front
        above_ground = M.bottom_line is None or b.bottom <= (M.bottom_line.y1 + M.bottom_line.y2) / 2 + 0.05 * tb.h
        not_whole_truck = b.w < 0.9 * tb.w or b.h < 0.9 * tb.h
        ix = max(0, min(b.xyxy[2], tb.xyxy[2]) - max(b.xyxy[0], tb.xyxy[0]))
        iy = max(0, min(b.xyxy[3], tb.xyxy[3]) - max(b.xyxy[1], tb.xyxy[1]))
        overlap = ix * iy / max(1, b.w * b.h)                      # share of the cargo box inside the truck box
        return inside_x and bottom_ok and above_ground and not_whole_truck and overlap >= 0.5
    cargo = [b for b in det.by_label("cargo", "container", "tarpaulin", "car") if _on_truck(b)]
    if cargo and det.truck_mask is not None:
        big = max(cargo, key=lambda b: b.w * b.h)
        # cargo extent = union of all cargo boxes on the truck (several cars on a carrier)
        c_l = min(b.xyxy[0] for b in cargo); c_r = max(b.xyxy[2] for b in cargo)
        # body extent is read at deck height (wheel-centre row): cargo sits above the deck, so the
        # mask row there is chassis + deck only, even when the mask also covers the cargo.
        if wheels:
            y = int(np.clip(np.median([(w.xyxy[1] + w.xyxy[3]) / 2 for w in wheels]), 0, H - 1))
        else:
            y = int(np.clip(tb.xyxy[3] - 0.25 * tb.h, 0, H - 1))
        xs = np.flatnonzero(det.truck_mask[y])
        if len(xs) > 10:
            body_l, body_r = int(xs.min()), int(xs.max())
            over_l = body_l - c_l
            over_r = c_r - body_r
            over_px = max(over_l, over_r, 0)
            if M.scale_m_per_px:
                if over_px == over_l and over_l > 0:
                    M.overhang_px = (body_l, c_l, y)
                elif over_r > 0:
                    M.overhang_px = (body_r, c_r, y)
                M.overhang_cm = round(over_px * M.scale_m_per_px * 100, 1)
                M.overhang_kind = "rear" if M.view == "side" else "side"
                M.overhang_conf = round(big.conf * (0.9 if M.view != "unknown" else 0.5), 2)
            else:
                M.notes.append("overhang: no scale object (wheel/body) found")
        else:
            M.notes.append("overhang: body edge not found at cargo height")
    elif M.view == "rear" and veh is not tb and det.truck_mask is not None and M.scale_m_per_px:
        # load above the vehicle box: compare the mask width above the body with the body width at the chassis row
        y = int(np.clip(veh.xyxy[1] + veh.h * 0.5, 0, H - 1))
        xs = np.flatnonzero(det.truck_mask[y])
        upper = det.truck_mask[max(0, tb.xyxy[1]): max(1, veh.xyxy[1] - int(0.05 * tb.h))]
        ux = np.flatnonzero(upper.any(axis=0)) if upper.size else []
        if len(xs) > 10 and len(ux) > 10:
            body_l, body_r = int(xs.min()), int(xs.max()); c_l, c_r = int(ux.min()), int(ux.max())
            over_l, over_r = body_l - c_l, c_r - body_r
            over_px = max(over_l, over_r, 0)
            M.overhang_px = (body_l, c_l, y) if over_l >= over_r else (body_r, c_r, y)
            M.overhang_cm = round(over_px * M.scale_m_per_px * 100, 1)
            M.overhang_kind = "side"
            M.overhang_conf = 0.6
            M.notes.append("overhang: load width from the mask above the body")
        else:
            M.notes.append("overhang: no cargo detected")
    else:
        M.notes.append("overhang: no cargo detected")

    # ---- load lean: only for a stacked load above the vehicle box in a rear view ----
    if M.view == "rear" and veh is not tb and det.truck_mask is not None:
        y0, y1_ = int(tb.xyxy[1]), int(veh.xyxy[1] - 0.05 * tb.h)
        if y1_ - y0 > 0.15 * tb.h:
            L, R = [], []
            for y in range(y0, y1_):
                xs = np.flatnonzero(det.truck_mask[y])
                if len(xs) > 10:
                    L.append((y, xs.min())); R.append((y, xs.max()))
            fl = _fit_line_ransac(np.array(L, dtype=float), tol=4.0) if len(L) >= 10 else None
            fr = _fit_line_ransac(np.array(R, dtype=float), tol=4.0) if len(R) >= 10 else None
            if fl and fr:
                # x = m*y + c ; m > 0 means x grows downward, i.e. the top is further LEFT
                al, ar_ = np.degrees(np.arctan(fl[0])), np.degrees(np.arctan(fr[0]))
                M.load_lean_deg = round(float((al + ar_) / 2), 1)
                M.load_spread_deg = round(float(al - ar_), 1)
                M.load_conf = round(float(min(fl[2], fr[2])) * min(1.0, (y1_ - y0) / (0.3 * tb.h)), 2)
                for m_, c_ in ((fl[0], fl[1]), (fr[0], fr[1])):
                    M.load_lines.append((int(m_ * y0 + c_), y0, int(m_ * y1_ + c_), y1_))
                M.notes.append("load lean from the two side edges of the stack")

    # ---- height ----
    ground_y = None
    if wheels:
        ground_y = float(np.median([w.bottom for w in wheels]))
    elif M.bottom_line is not None:
        ground_y = (M.bottom_line.y1 + M.bottom_line.y2) / 2
    # cargo top = highest point of anything riding on the truck: the cargo boxes, the truck mask, and any
    # other detection that rests on the truck (bottom inside the truck box, >= 60 % horizontal overlap).
    # A tall machine on a low-loader is often not a "cargo" box and not part of the COCO truck mask.
    tops = [float(tb.xyxy[1])]
    if det.truck_mask is not None:
        ys = np.flatnonzero(det.truck_mask.any(axis=1))
        if len(ys):
            tops.append(float(ys.min()))
    tops += [float(b.xyxy[1]) for b in cargo]
    for b in det.boxes:
        if b.label == "wheel" or b is tb:
            continue
        ix = max(0, min(b.xyxy[2], tb.xyxy[2]) - max(b.xyxy[0], tb.xyxy[0]))
        rests = tb.xyxy[1] <= b.bottom <= tb.xyxy[3] + 0.05 * tb.h
        if ix >= 0.6 * b.w and rests and b.xyxy[1] < tb.xyxy[1] and b.conf >= 0.25:
            tops.append(float(b.xyxy[1]))
            M.notes.append(f"height: top from {b.label} box above the truck")
    top_y = min(tops) if cargo or det.truck_mask is not None else None
    if ground_y and top_y is not None and M.scale_m_per_px:
        M.height_m = round((ground_y - top_y) * M.scale_m_per_px, 2)
        M.height_conf = round(0.8 if wheels else (0.7 if M.scale_source.startswith("body width") else 0.4), 2)
        M.height_px = (int(tb.cx), int(top_y), int(ground_y))
    else:
        M.notes.append("height: missing ground line or scale")
    return M
