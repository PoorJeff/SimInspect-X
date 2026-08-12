# Gauge Synthetic Dataset

Synthetic analog gauge images for training and evaluating gauge reading algorithms.

## Generation
```bash
pip install opencv-python numpy
python generate_dataset.py datasets/gauge_synthetic
```

## Parameters
Each image is randomly parameterized:
- **Pointer angle**: uniform across full scale (-120 to +120 arc)
- **Scale**: 0-100 psi, 0-200 kPa, 0-60 bar, 0-160 psi
- **Blur**: Gaussian sigma 0-2.0
- **Brightness**: 0.5-1.0 factor
- **Perspective**: random homography warp (strength 0-0.6)
- **Occlusion**: random rectangle covering 0-50% of image
- **Noise**: Gaussian sigma 0-2.0

## Structure
```
train/
  images/  (500 PNG, 320x320)
  labels.csv
test/
  images/  (100 PNG, 320x320)
  labels.csv
```

## Labels CSV
`image_id, angle_deg, value, unit, blur, brightness, occlusion, noise_level`
