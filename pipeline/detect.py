"""Detection stage: open-vocabulary boxes (YOLO-World) + truck mask (YOLOv8-seg).

Both models are pretrained and downloaded by ultralytics on first use.
Nothing here is trained by us; the system's own logic lives in geometry.py
and decision.py.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import torch
import yaml
from ultralytics import YOLO

CFG_PATH = Path(__file__).with_name("config.yaml")
CFG = yaml.safe_load(CFG_PATH.read_text())

PRIVACY_PROMPTS = ["license plate", "person", "face"]
COCO_TRUCK_IDS = {7, 5}  # truck, bus (bus mask helps on box-body trucks)


@dataclass
class Box:
    label: str
    conf: float
    xyxy: tuple[int, int, int, int]

    @property
    def w(self):
        return self.xyxy[2] - self.xyxy[0]

    @property
    def h(self):
        return self.xyxy[3] - self.xyxy[1]

    @property
    def cx(self):
        return (self.xyxy[0] + self.xyxy[2]) / 2

    @property
    def bottom(self):
        return self.xyxy[3]


@dataclass
class Detections:
    boxes: list[Box] = field(default_factory=list)
    privacy_boxes: list[Box] = field(default_factory=list)
    truck_mask: np.ndarray | None = None  # uint8 HxW, 255 inside truck
    truck_box: Box | None = None
    timings_ms: dict = field(default_factory=dict)

    def by_label(self, *labels):
        return [b for b in self.boxes if b.label in labels]


class Detector:
    def __init__(self):
        import os
        dev = os.environ.get("LSG_DEVICE", CFG["detector"]["device"])
        if dev == "auto":
            dev = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = dev
        self.world = YOLO(CFG["detector"]["model"])
        self.prompts = list(CFG["detector"]["prompts"]) + PRIVACY_PROMPTS
        self.world.set_classes(self.prompts)
        self.seg = YOLO("yolov8s-seg.pt")
        self.conf = CFG["detector"]["conf"]
        self.imgsz = CFG["detector"]["imgsz"]

    def __call__(self, img: np.ndarray) -> Detections:
        det = Detections()
        h, w = img.shape[:2]

        t0 = time.perf_counter()
        r = self.world.predict(img, conf=self.conf, imgsz=self.imgsz, device=self.device, verbose=False)[0]
        det.timings_ms["world"] = (time.perf_counter() - t0) * 1000
        for b, c, k in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy(), r.boxes.cls.cpu().numpy()):
            box = Box(self.prompts[int(k)], float(c), tuple(int(v) for v in b))
            if box.label in PRIVACY_PROMPTS:
                det.privacy_boxes.append(box)
            else:
                det.boxes.append(box)

        t0 = time.perf_counter()
        s = self.seg.predict(img, conf=0.25, imgsz=self.imgsz, device=self.device, verbose=False)[0]
        det.timings_ms["seg"] = (time.perf_counter() - t0) * 1000
        best, best_area = None, 0
        if s.masks is not None:
            for m, c, k, b in zip(s.masks.data.cpu().numpy(), s.boxes.conf.cpu().numpy(),
                                  s.boxes.cls.cpu().numpy(), s.boxes.xyxy.cpu().numpy()):
                if int(k) in COCO_TRUCK_IDS:
                    area = float(m.sum())
                    if area > best_area:
                        best_area, best = area, (m, c, b)
                elif int(k) == 0:  # person from COCO as extra privacy source
                    det.privacy_boxes.append(Box("person", float(c), tuple(int(v) for v in b)))
        if best is not None:
            m, c, b = best
            mask = cv2.resize((m * 255).astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
            det.truck_mask = mask
            det.truck_box = Box("truck", float(c), tuple(int(v) for v in b))
        else:
            # fall back to the largest world-model truck/trailer box
            cands = det.by_label("truck", "trailer")
            if cands:
                det.truck_box = max(cands, key=lambda bb: bb.w * bb.h)
        return det
