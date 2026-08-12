# rewrite
"""Read gauge value using color-based needle detection + angular histogram."""
import cv2, math, numpy as np

ARC_START = -120; ARC_END = 120; ARC_RANGE = 240

class GaugeReader:
    def __init__(self, min_val=0, max_val=100, unit="psi"):
        self.min = min_val; self.max = max_val; self.unit = unit

    def read(self, roi, cx, cy, r):
        h, w = roi.shape[:2]; rr = int(r * 0.85)
        B = roi[:,:,0].astype(np.float32); G = roi[:,:,1].astype(np.float32); R = roi[:,:,2].astype(np.float32)
        needle_map = np.clip(2 * B - G - R - 30, 0, 255).astype(np.uint8)
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, (cx, cy), rr, 255, -1)
        needle_map = cv2.bitwise_and(needle_map, needle_map, mask=mask)
        bins = 360; hist = np.zeros(bins)
        ys, xs = np.where(needle_map > 20)
        for y, x in zip(ys, xs):
            dx, dy = x - cx, cy - y
            ang = int((math.degrees(math.atan2(dy, dx)) + 180) % 360)
            hist[ang] += needle_map[y, x]
        best_ang = None; best_score = 0
        for deg in range(ARC_START + 180, ARC_END + 181):
            idx = deg % 360
            score = hist[idx] + hist[(idx+1)%360] + hist[(idx-1)%360]
            if score > best_score:
                best_score = score; best_ang = deg - 180
        if best_ang is None:
            return (self.min + self.max) / 2, 0.0
        ang = max(ARC_START, min(ARC_END, best_ang))
        frac = (ang - ARC_START) / ARC_RANGE
        val = self.min + frac * (self.max - self.min)
        conf = min(1.0, best_score / max(1, hist.sum() * 0.05))
        return val, conf
