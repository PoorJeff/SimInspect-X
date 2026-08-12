#!/usr/bin/env python3
"""Confidence proxy fusing detection, pointer strength, area,
   view angle, and consistency. Weighted geometric mean."""
import math

class ConfidenceEstimator:
    def __init__(self, w_detect=0.30, w_strength=0.25,
                 w_area=0.15, w_angle=0.15, w_consistency=0.15):
        self.w = [w_detect, w_strength, w_area, w_angle, w_consistency]

    def estimate(self, detection_ok, pointer_strength,
                 gauge_radius, img_size, axis_ratio, consistency):
        f1 = 1.0 if detection_ok else 0.1
        f2 = max(0.0, min(1.0, pointer_strength))
        expected_r = img_size / 2.3
        f3 = min(1.0, (gauge_radius / expected_r) ** 0.5)
        f4 = 1.0 / (1.0 + abs(1.0 - axis_ratio) * 4)
        f5 = max(0.0, min(1.0, consistency))
        eps = 1e-6
        log_conf = (
            self.w[0] * math.log(max(f1, eps)) +
            self.w[1] * math.log(max(f2, eps)) +
            self.w[2] * math.log(max(f3, eps)) +
            self.w[3] * math.log(max(f4, eps)) +
            self.w[4] * math.log(max(f5, eps)))
        return math.exp(log_conf)
