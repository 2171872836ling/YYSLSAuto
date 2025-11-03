[English](./README.en.md) | **中文**
<h1>燕云十六声自动化</h1>

#### （1）OCR 需要的库：
1. OCR加速的库，根据自己显卡版本安装：`pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu`
2. `cv2` 库：`pip install opencv-python`
3. `easyocr` 库：`pip install easyocr`
   - BitBlt：内存（缓存）截图
   - EasyOCR：流行的OCR识别第三方库，内含识别大模型
   - 两者结合加快识别速度

#### （2）键盘模拟：
- **单击**：200~500毫秒时间内，按下一次
- **双击**：200~500毫秒时间内，按下两次
- **长按**：大于500秒时间外，按下一次
- **鼠标后摇**：10~25毫秒
- **按键后摇**：100~250毫秒
- **统一后摇**：0~250毫秒
- **统一单击按下和弹起的时间延迟**：300毫秒
- **统一双击按下和弹起的时间延迟**：500毫秒
- 封装后所有操作在1000毫秒内实现