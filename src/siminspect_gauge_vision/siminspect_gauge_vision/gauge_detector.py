#!/usr/bin/env python3
"""Detect gauge ROI and locate center via HoughCircles."""
import cv2, numpy as np

class GaugeDetector:
    def __init__(self, min_r=80, max_r=160, cl=50, ch=150):
        self.min_r = min_r; self.max_r = max_r
        self.cl = cl; self.ch = ch

    def detect(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2,
            minDist=100, param1=self.ch, param2=30,
            minRadius=self.min_r, maxRadius=self.max_r)
        if circles is None:
            return self._fallback(img)

        cx, cy, r = map(int, circles[0, 0])
        m = int(r * 0.15)
        x1, y1 = max(0, cx - r - m), max(0, cy - r - m)
        x2 = min(img.shape[1], cx + r + m)
        y2 = min(img.shape[0], cy + r + m)
        roi = img[y1:y2, x1:x2]
        return roi, (cx - x1, cy - y1), r, True

    def _fallback(self, img):
        h, w = img.shape[:2]
        return img, (w//2, h//2), min(w, h)//2 - 10, False
