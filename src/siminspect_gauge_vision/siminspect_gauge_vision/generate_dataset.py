#!/usr/bin/env python3
"""Synthetic analog gauge image generator. Pure Python, no ROS."""
import cv2, csv, math, os, random, sys
import numpy as np
SIZE = 320; CX = 160; R = 140; NL = 105

def draw_gauge(angle_deg, min_val, max_val, unit):
    img = np.ones((SIZE, SIZE, 3), dtype=np.uint8) * 245
    cv2.circle(img, (CX, CX), R + 8, (180, 180, 180), 3)
    cv2.circle(img, (CX, CX), R, (255, 255, 255), -1)
    cv2.circle(img, (CX, CX), R, (100, 100, 100), 2)
    vr = max_val - min_val
    for i in range(0, 241, 10):
        a = math.radians(-120 + i)
        r1 = R - (12 if i % 30 == 0 else 8); r2 = R - 2
        x1 = int(CX + r1 * math.cos(a)); y1 = int(CX - r1 * math.sin(a))
        x2 = int(CX + r2 * math.cos(a)); y2 = int(CX - r2 * math.sin(a))
        cv2.line(img, (x1, y1), (x2, y2), (50, 50, 50), 2 if i % 30 == 0 else 1)
    for i in range(0, 241, 30):
        a = math.radians(-120 + i); v = min_val + vr * i / 240
        tx = int(CX + (R - 25) * math.cos(a)) - 12
        ty = int(CX - (R - 25) * math.sin(a)) + 5
        cv2.putText(img, str(round(v)), (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (50,50,50), 1)
    cv2.putText(img, unit, (CX-15, CX+50), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80,80,80), 1)
    rad = math.radians(angle_deg)
    nx = int(CX + NL * math.cos(rad)); ny = int(CX - NL * math.sin(rad))
    cv2.line(img, (CX, CX), (nx, ny), (200, 30, 30), 3)
    cv2.circle(img, (CX, CX), 8, (80, 80, 80), -1)
    return img

def do_blur(img, lv): return cv2.GaussianBlur(img,(0,0),sigmaX=lv) if lv>0 else img
def do_bright(img, f): h=cv2.cvtColor(img,cv2.COLOR_BGR2HSV); h[:,:,2]=np.clip(h[:,:,2]*f,0,255).astype(np.uint8); return cv2.cvtColor(h,cv2.COLOR_HSV2BGR)
def do_persp(img, s):
    if s==0: return img
    S=s*15; w=SIZE; src=np.float32([[0,0],[w,0],[0,w],[w,w]])
    dst=np.float32([[S,S],[w-S,S*.7],[S*.5,w-S],[w-S*.5,w-S*.5]])
    return cv2.warpPerspective(img,cv2.getPerspectiveTransform(src,dst),(w,w),borderValue=(245,245,245))
def do_occ(img, lv):
    if lv<=0: return img
    ox=random.randint(SIZE//4,SIZE-SIZE//4); oy=random.randint(SIZE//4,SIZE-SIZE//4)
    ow=int(SIZE*lv*.4+random.random()*.3*SIZE); oh=int(SIZE*lv*.3+random.random()*.2*SIZE)
    cv2.rectangle(img,(max(0,ox),max(0,oy)),(min(SIZE,ox+ow),min(SIZE,oy+oh)),(80,80,80),-1); return img
def do_noise(img, lv):
    n=np.random.normal(0,lv*20,img.shape).astype(np.int16)
    return np.clip(img.astype(np.int16)+n,0,255).astype(np.uint8)

def generate(out_dir, count, split):
    d=os.path.join(out_dir,split,"images"); os.makedirs(d,exist_ok=True); labels=[]
    cfgs=[{"min":0,"max":100,"unit":"psi"},{"min":0,"max":200,"unit":"kPa"},{"min":0,"max":60,"unit":"bar"},{"min":0,"max":160,"unit":"psi"}]
    for i in range(count):
        c=random.choice(cfgs); vr=c["max"]-c["min"]
        val=random.uniform(c["min"],c["max"]); frac=(val-c["min"])/vr
        ang=-120+frac*240
        bl=random.choice([0,0,0,0.5,1.0,1.5,2.0])
        br=random.choice([0.5,0.7,0.85,1.0,1.0,1.0])
        ps=random.choice([0,0,0,0.2,0.4,0.6])
        oc=random.choice([0,0,0,0.15,0.3,0.5])
        nl=random.choice([0,0,0,0.5,1.0,2.0])
        img=draw_gauge(ang,c["min"],c["max"],c["unit"])
        if bl>0: img=do_blur(img,bl)
        if br!=1.0: img=do_bright(img,br)
        if ps>0: img=do_persp(img,ps)
        if oc>0: img=do_occ(img,oc)
        if nl>0: img=do_noise(img,nl)
        iid=f"{split}_{i:04d}"
        cv2.imwrite(os.path.join(d,f"{iid}.png"),img)
        labels.append([iid,round(ang,3),round(val,3),c["unit"],round(bl,2),round(br,2),round(oc,2),round(nl,2)])
    with open(os.path.join(out_dir,split,"labels.csv"),"w",newline="") as f:
        w=csv.writer(f); w.writerow(["image_id","angle_deg","value","unit","blur","brightness","occlusion","noise_level"]); w.writerows(labels)
    print(f"{split}: {count} images")

if __name__=="__main__":
    random.seed(42); np.random.seed(42)
    out=sys.argv[1] if len(sys.argv)>1 else "datasets/gauge_synthetic"
    generate(out,500,"train"); generate(out,100,"test")
    print(f"Dataset complete: {out}")
