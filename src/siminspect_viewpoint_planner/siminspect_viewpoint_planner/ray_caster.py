# ray_caster
"""2D Bresenham ray-casting with occupancy grid."""
import numpy as np

class RayCaster:
    def __init__(self, res=0.1, w=100, h=100):
        self.res = res; self.grid = np.zeros((h,w), dtype=np.uint8)
        self.ox = 0; self.oy = 0
    def set_origin(self, x, y): self.ox = x; self.oy = y
    def add_box(self, cx, cy, w, h):
        x1 = int((cx-w/2-self.ox)/self.res); y1 = int((cy-h/2-self.oy)/self.res)
        x2 = x1 + int(w/self.res); y2 = y1 + int(h/self.res)
        x1 = max(0,x1); y1 = max(0,y1)
        x2 = min(self.grid.shape[1],x2); y2 = min(self.grid.shape[0],y2)
        if x1<x2 and y1<y2: self.grid[y1:y2,x1:x2] = 1
    def add_circle(self, cx, cy, r):
        for y in range(self.grid.shape[0]):
            for x in range(self.grid.shape[1]):
                wx = self.ox+x*self.res; wy = self.oy+y*self.res
                if (wx-cx)**2+(wy-cy)**2 < r**2: self.grid[y,x] = 1
    def visible(self, x0, y0, x1, y1):
        sx=int((x0-self.ox)/self.res); sy=int((y0-self.oy)/self.res)
        ex=int((x1-self.ox)/self.res); ey=int((y1-self.oy)/self.res)
        dx=abs(ex-sx); dy=-abs(ey-sy)
        sx_s=1 if sx<ex else -1; sy_s=1 if sy<ey else -1
        err=dx+dy
        while True:
            if sx==ex and sy==ey: return True
            if 0<=sy<self.grid.shape[0] and 0<=sx<self.grid.shape[1]:
                if self.grid[sy,sx]==1: return False
            e2=2*err
            if e2>=dy: err+=dy; sx+=sx_s
            if e2<=dx: err+=dx; sy+=sy_s
