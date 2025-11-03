[中文](./README.en.md) | **English**
<h1>YYSLSAuto</h1>
#### (1) Libraries Required for OCR:
1. Library for OCR acceleration, install according to your graphics card version: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu`
2. `cv2` library: `pip install opencv-python`
3. `easyocr` library: `pip install easyocr`
   - BitBlt: Memory (cache) for screenshots
   - EasyOCR: Popular third-party OCR recognition library, includes large recognition models
   - Combining the two speeds up recognition

#### (2) Mouse and Keyboard Simulation:
- **Single Click**: Within 200~500 milliseconds, press once
- **Double Click**: Within 200~500 milliseconds, press twice
- **Long Press**: Outside of 500 milliseconds, press once
- **Mouse After Shake**: 10~25 milliseconds
- **Key Press After Shake**: 100~250 milliseconds
- **Unified After Shake**: 0~250 milliseconds
- **Unified Delay for Single Click Press and Release**: 300 milliseconds
- **Unified Delay for Double Click Press and Release**: 500 milliseconds
- All operations are encapsulated to be completed within 1000 milliseconds