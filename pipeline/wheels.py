"""Wheel finder without a trained detector: Hough circles in the lower band of the truck,
validated against the truck mask (inside the silhouette, touching its bottom edge, dark interior).
Also provides a ground line from the lowest silhouette points (tyre contact patches)."""
from __future__ import annotations

import cv2
import numpy as np

from .detect import Box


def ground_points(mask: np.ndarray, x_lo: int, x_hi: int, truck_h: int):
    """Lowest silhouette points per column, keep those near the overall lowest level (contact patches)."""
    pts = []
    for x in range(x_lo, x_hi):
        ys = np.flatnonzero(mask[:, x])
        if len(ys):
            pts.append((x, ys.max()))
    if len(pts) < 10:
        return None
    pts = np.array(pts, dtype=float)
    # robust "lowest level": 97th percentile of y, keep points within 4% of truck height of it
    y_low = np.percentile(pts[:, 1], 97)
    keep = pts[pts[:, 1] >= y_low - 0.04 * truck_h]
    return keep if len(keep) >= 6 else None


def find_wheels(img: np.ndarray, mask: np.ndarray, tb: Box) -> list[Box]:
    H, W = img.shape[:2]
    x1, y1, x2, y2 = tb.xyxy
    th = max(y2 - y1, 1)
    by1, by2 = y1 + int(th * 0.45), min(H, y2 + int(th * 0.08))
    bx1, bx2 = max(0, x1 - 10), min(W, x2 + 10)
    band = img[by1:by2, bx1:bx2]
    if band.size == 0:
        return []
    f = min(1.0, 300.0 / th)                      # work at ~300 px truck height for speed
    g = cv2.cvtColor(band, cv2.COLOR_BGR2GRAY)
    if f < 1.0:
        g = cv2.resize(g, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    g = cv2.createCLAHE(2.0, (8, 8)).apply(g)
    g = cv2.medianBlur(g, 5)
    ths = th * f
    # wheel radius bound: in a side view a 1.05 m wheel is at most ~11 % of the rig length (>= 5 m), so bound
    # by width there; the box height is unreliable because a tall load is often inside the truck mask.
    tw = max(x2 - x1, 1)
    side = tw / th >= 1.6
    rmax_px = th * 0.22 if not side else min(th * 0.22, tw * 0.11)
    rmin_px = th * 0.05
    rmin, rmax = max(5, int(rmin_px * f)), max(6, int(rmax_px * f))
    c = cv2.HoughCircles(g, cv2.HOUGH_GRADIENT, dp=1.2, minDist=int(ths * 0.15), param1=120, param2=30,
                         minRadius=rmin, maxRadius=rmax)
    if c is None:
        return []
    c = c / f                                      # back to full-resolution band coordinates
    # bottom of silhouette per column
    bottom = np.full(W, -1)
    cols = np.flatnonzero(mask.any(axis=0))
    for x in cols:
        bottom[x] = np.flatnonzero(mask[:, x]).max()
    out = []
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    for cx, cy, r in c[0]:
        cx, cy, r = int(cx) + bx1, int(cy) + by1, int(r)
        if not (0 <= cx < W):
            continue
        # 1) circle bottom close to silhouette bottom at that column
        if bottom[cx] < 0 or abs((cy + r) - bottom[cx]) > 0.06 * th:
            continue
        # 2) circle mostly inside the mask (computed on a local crop)
        R = int(1.6 * r) + 1
        ya, yb, xa, xb = max(0, cy - R), min(H, cy + R), max(0, cx - R), min(W, cx + R)
        yy, xx = np.ogrid[ya:yb, xa:xb]
        d2 = (xx - cx) ** 2 + (yy - cy) ** 2
        disc = d2 <= r * r
        if not disc.any():
            continue
        if mask[ya:yb, xa:xb][disc].astype(bool).mean() < 0.6:
            continue
        # 3) darker than the ring around it
        ring = (d2 <= (1.6 * r) ** 2) & ~disc
        gcrop = gray[ya:yb, xa:xb]
        if ring.any() and gcrop[disc].mean() > gcrop[ring].mean() + 10:
            continue
        out.append(Box("wheel", 0.5, (cx - r, cy - r, cx + r, cy + r)))
    # de-duplicate overlapping circles
    out.sort(key=lambda b: b.xyxy[0])
    dedup = []
    for b in out:
        if dedup and b.xyxy[0] < dedup[-1].xyxy[2] - 0.3 * b.w:
            continue
        dedup.append(b)
    return dedup


def structural_angle(img: np.ndarray, mask: np.ndarray, tb: Box):
    """Length-weighted median angle (deg) of long near-horizontal edges inside the truck silhouette.
    Chassis, deck rails, skirts and body seams are parallel to the chassis, so their common angle
    tracks body roll even when the top edge is irregular (car carriers, open loads).
    Returns (angle_deg, confidence 0..1, lines) or None."""
    x1, y1, x2, y2 = tb.xyxy
    H, W = img.shape[:2]
    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(W, x2), min(H, y2)
    crop = img[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    f = min(1.0, 640.0 / max(crop.shape[:2]))
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    m = mask[y1:y2, x1:x2]
    if f < 1.0:
        g = cv2.resize(g, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        m = cv2.resize(m, (g.shape[1], g.shape[0]), interpolation=cv2.INTER_NEAREST)
    m = cv2.erode(m, np.ones((7, 7), np.uint8))      # drop the silhouette outline itself
    e = cv2.Canny(g, 60, 160) & m
    w = g.shape[1]
    lines = cv2.HoughLinesP(e, 1, np.pi / 360, threshold=40, minLineLength=int(w * 0.18), maxLineGap=8)
    if lines is None:
        return None
    angs, lens, keep = [], [], []
    for lx1, ly1, lx2, ly2 in lines.reshape(-1, 4):
        a = np.degrees(np.arctan2(ly2 - ly1, lx2 - lx1))
        if a > 90: a -= 180
        if a < -90: a += 180
        if abs(a) > 20:
            continue
        angs.append(a); lens.append(np.hypot(lx2 - lx1, ly2 - ly1))
        keep.append((int(lx1 / f) + x1, int(ly1 / f) + y1, int(lx2 / f) + x1, int(ly2 / f) + y1))
    if not angs:
        return None
    angs, lens = np.array(angs), np.array(lens)
    order = np.argsort(angs); cum = np.cumsum(lens[order]); med = angs[order][np.searchsorted(cum, cum[-1] / 2)]
    spread = np.sqrt(np.average((angs - med) ** 2, weights=lens))
    conf = float(min(1.0, lens.sum() / (2.0 * w)) * max(0.0, 1.0 - spread / 6.0))
    return float(med), round(conf, 2), keep


def _vertical_lines(img: np.ndarray, region: np.ndarray, min_len_frac: float, max_dev_deg: float = 15.0):
    """Long near-vertical Canny/Hough segments inside `region` (uint8 mask). Returns list of (angle_from_vertical_deg, length, seg)."""
    H, W = img.shape[:2]
    f = min(1.0, 800.0 / max(H, W))
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    m = region
    if f < 1.0:
        g = cv2.resize(g, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        m = cv2.resize(m, (g.shape[1], g.shape[0]), interpolation=cv2.INTER_NEAREST)
    e = cv2.Canny(g, 60, 160) & m
    min_len = max(15, int(g.shape[0] * min_len_frac))
    lines = cv2.HoughLinesP(e, 1, np.pi / 360, threshold=30, minLineLength=min_len, maxLineGap=6)
    out = []
    if lines is None:
        return out
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        dx, dy = x2 - x1, y2 - y1
        if dy == 0:
            continue
        a = np.degrees(np.arctan2(dx, -dy))          # 0 = straight up; positive = leaning right
        if a > 90: a -= 180
        if a < -90: a += 180
        if abs(a) > max_dev_deg:
            continue
        out.append((float(a), float(np.hypot(dx, dy)), (int(x1 / f), int(y1 / f), int(x2 / f), int(y2 / f))))
    return out


def _wmedian(vals, weights):
    o = np.argsort(vals); c = np.cumsum(np.asarray(weights)[o]); return float(np.asarray(vals)[o][np.searchsorted(c, c[-1] / 2)])


def body_vertical(img: np.ndarray, mask: np.ndarray, tb: Box):
    """Lean of the truck body relative to the image vertical, from near-vertical edges inside the silhouette.
    Left-half and right-half edges converge in opposite directions under camera pitch, so averaging the two
    halves cancels perspective to first order. Returns (lean_deg, conf, segs) or None."""
    region = cv2.erode(mask, np.ones((5, 5), np.uint8))
    ls = _vertical_lines(img, region, min_len_frac=0.06)
    if not ls:
        return None
    cx = tb.cx
    L = [l for l in ls if (l[2][0] + l[2][2]) / 2 < cx]
    R = [l for l in ls if (l[2][0] + l[2][2]) / 2 >= cx]
    parts = []
    for side in (L, R):
        if side:
            parts.append((_wmedian([l[0] for l in side], [l[1] for l in side]), sum(l[1] for l in side)))
    if not parts:
        return None
    lean = float(np.mean([p[0] for p in parts]))
    total = sum(p[1] for p in parts)
    conf = min(1.0, total / (1.5 * tb.h)) * (1.0 if len(parts) == 2 else 0.5)
    segs = [l[2] for l in sorted(ls, key=lambda l: -l[1])[:10]]
    return lean, round(float(conf), 2), segs


def scene_vertical(img: np.ndarray, mask: np.ndarray):
    """Gravity reference from long vertical edges OUTSIDE the truck (poles, walls, door frames).
    Returns (angle_deg, conf, segs) or None."""
    H, W = img.shape[:2]
    outside = cv2.bitwise_not(cv2.dilate(mask, np.ones((25, 25), np.uint8)))
    ls = _vertical_lines(img, outside, min_len_frac=0.12, max_dev_deg=10.0)
    if len(ls) < 2:
        return None
    ang = _wmedian([l[0] for l in ls], [l[1] for l in ls])
    spread = np.sqrt(np.average((np.array([l[0] for l in ls]) - ang) ** 2, weights=[l[1] for l in ls]))
    conf = min(1.0, sum(l[1] for l in ls) / (2.0 * H)) * max(0.0, 1.0 - spread / 4.0)
    return float(ang), round(float(conf), 2), [l[2] for l in ls[:8]]
