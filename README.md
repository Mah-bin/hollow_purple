# Hollow Purple 🟣
A real-time hand gesture-controlled visual effect inspired by the anime Jujutsu Kaisen. Use your hands in front of a webcam to summon, merge, and throw orbs, culminating in a dramatic Hollow Purple screen explosion.

##  Demo Flow

https://github.com/user-attachments/assets/27b9f917-4411-4a6d-b720-ad4351994514

1. Show your left index finger → a blue orb appears 🔵

2. Show your right index finger → a red orb appears 🔴

3. Bring both hands together → orbs merge into purple 🟣

4. Pinch your right index and middle fingers, then flick forward → the purple orb expands and explodes

5. The screen fills with Hollow Purple

## Features

- Real-time hand tracking via MediaPipe

- Two-hand orb summoning with particle trails
 
- Orb merge detection when hands come close

- Flick/pinch gesture recognition for throwing

- Radial expansion animation with ring particles

• Full-screen purple overlay on explosion

## Requirements

- Python 3.8+

- Webcam

### Dependencies
```bash
pip install opencv-python mediapipe numpy
```

### Controls

| Action | Gesture |
|---|---|
| Summon blue orb | Show left index finger |
| Summon red orb | Show right index finger |
| Merge orbs | Bring both index fingers close together |
| Throw / explode | Pinch right index + middle finger, then flick forward |
| Reset | Press `r` |
| Quit | Press `q` |

## How It Works

### - Hand Tracking
MediaPipe's `Hands` solution tracks up to 2 hands at 60 FPS. Landmark 8 (index fingertip) and landmark 12 (middle fingertip) are used for orb positioning and gesture detection.

### - Merge Detection
When the distance between the left and right index fingertips falls below `120px`, the orbs merge at their midpoint into a single purple orb.

### - Flick Gesture
After merging, the app watches for a **pinch** (index and middle fingertips within `60px`) followed by a **forward movement** of more than `100px` while pinched. This triggers the throw.

### - Explosion Animation
The purple orb expands radially at `20px` per frame, emitting ring particles. Once it reaches `400px` radius, the screen instantly fills with a full-opacity purple overlay.

### - Particle System
Each `Particle` has randomized velocity, gravity, size, and lifetime. Opacity fades as particles age. Particles are drawn using alpha blending via `cv2.addWeighted`.

## Notes

- The app uses a **mirrored camera view**, so MediaPipe's "Left" label maps to the user's right hand and vice versa.
- Camera is set to `1280×720` at `60 FPS` — lower these values in `run()` if performance is poor on your machine.
- The `create_explosion_particles` method exists but is not currently called in the main flow; it can be wired in for additional effects.

## License

MIT — free to use, modify, and distribute.
