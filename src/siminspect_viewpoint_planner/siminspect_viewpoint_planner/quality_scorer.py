#!/usr/bin/env python3
"""Compute Q(v,a) = wV*V + wD*D + wA*A + wS*S - wT*T per 07 spec."""
import math

DEFAULT_W = {"w_vis":0.35,"w_d":0.25,"w_theta":0.25,"w_s":0.15,"w_t":0.15}
D_SAFE = 0.50

class QualityScorer:
    def __init__(self, weights=None, d_desired=0.8, theta_max_deg=40, d_safe=D_SAFE):
        w = weights or DEFAULT_W
        self.w_vis = w.get("w_vis", 0.35)
        self.w_d = w.get("w_d", 0.25)
        self.w_theta = w.get("w_theta", 0.25)
        self.w_s = w.get("w_s", 0.15)
        self.w_t = w.get("w_t", 0.15)
        self.d_desired = d_desired
        self.theta_max = math.radians(theta_max_deg)
        self.d_safe = d_safe

    def score_D(self, d): return max(0.0, 1.0 - abs(d - self.d_desired) / self.d_desired)

    def score_A(self, th): ct=math.cos(th); cm=math.cos(self.theta_max); return max(0.0,(ct-cm)/(1.0-cm)) if th<self.theta_max else 0.0
    def score_S(self, d_obs): return min(1.0, d_obs / self.d_safe)

    def score_all(self, vps, rx, ry, get_visible, get_dist, get_theta, get_clear):
        v_pos = []
        for i, vp in enumerate(vps):
            if not get_visible(i): vp.quality_score = 0.0; continue
            d = get_dist(i); th = get_theta(i); cl = get_clear(i)
            tr = math.hypot(vp.pose.position.x-rx, vp.pose.position.y-ry)
            v_pos.append((i, self.score_D(d), self.score_A(th), self.score_S(cl), tr))
        if not v_pos: return
        mt = max(t for _,_,_,_,t in v_pos)
        for i, Dv, Av, Sv, tr in v_pos:
            Tv = tr / mt if mt > 0 else 1.0
            vps[i].quality_score = self.w_vis*1.0 + self.w_d*Dv + self.w_theta*Av + self.w_s*Sv - self.w_t*Tv
