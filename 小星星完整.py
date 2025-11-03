import pydirectinput
import time
import threading

# 音符到键盘的映射
HIGH_OCTAVE = {
    '1': 'q', '2': 'w', '3': 'e', '4': 'r', '5': 't', '6': 'y', '7': 'u'
}

MID_OCTAVE = {
    '1': 'a', '2': 's', '3': 'd', '4': 'f', '5': 'g', '6': 'h', '7': 'j'
}

LOW_OCTAVE = {
    '1': 'z', '2': 'x', '3': 'c', '4': 'v', '5': 'b', '6': 'n', '7': 'm'
}

# 踏板控制键
PEDAL_KEY = 'space'

# 音符持续时间 (以秒为单位)
BPM = 120  # 小星星的常用速度
QUARTER = 60 / BPM  # 四分音符
EIGHTH = QUARTER / 2  # 八分音符
DOTTED_QUARTER = QUARTER * 1.5  # 附点四分音符


class KeyPressThread(threading.Thread):
    """键盘按键线程"""

    def __init__(self, key, duration, delay=0):
        super().__init__()
        self.key = key
        self.duration = duration
        self.delay = delay
        self._stop_event = threading.Event()

    def run(self):
        if self.delay > 0:
            time.sleep(self.delay)
        pydirectinput.keyDown(self.key)
        self._stop_event.wait(self.duration)
        pydirectinput.keyUp(self.key)

    def stop(self):
        self._stop_event.set()


class PedalController:
    """踏板控制器"""

    def __init__(self):
        self.pedal_thread = None

    def press_pedal(self, duration=QUARTER * 2):
        """踩下踏板"""
        if self.pedal_thread and self.pedal_thread.is_alive():
            self.pedal_thread.stop()
        self.pedal_thread = KeyPressThread(PEDAL_KEY, duration)
        self.pedal_thread.start()

    def release_pedal(self):
        """释放踏板"""
        if self.pedal_thread and self.pedal_thread.is_alive():
            self.pedal_thread.stop()


def play_note(notes, duration, pedal_controller=None):
    """播放音符"""
    threads = []

    # 对于长音符使用踏板
    use_pedal = (duration >= QUARTER) and (pedal_controller is not None)

    if use_pedal:
        pedal_controller.press_pedal(duration * 1.5)
        time.sleep(0.02)  # 踏板先于音符按下

    for octave, note in notes:
        if octave == 'high':
            key = HIGH_OCTAVE[note]
        elif octave == 'mid':
            key = MID_OCTAVE[note]
        elif octave == 'low':
            key = LOW_OCTAVE[note]

        thread = KeyPressThread(key, duration)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    if use_pedal:
        time.sleep(0.05)
        pedal_controller.release_pedal()


def twinkle_twinkle_little_star():
    """小星星主旋律"""
    # 小星星乐谱 (音符, 持续时间)
    melody = [
        # 第一句：一闪一闪亮晶晶
        ([('mid', '1')], QUARTER),
        ([('mid', '1')], QUARTER),
        ([('mid', '5')], QUARTER),
        ([('mid', '5')], QUARTER),
        ([('mid', '6')], QUARTER),
        ([('mid', '6')], QUARTER),
        ([('mid', '5')], DOTTED_QUARTER),

        # 第二句：满天都是小星星
        ([('mid', '4')], QUARTER),
        ([('mid', '4')], QUARTER),
        ([('mid', '3')], QUARTER),
        ([('mid', '3')], QUARTER),
        ([('mid', '2')], QUARTER),
        ([('mid', '2')], QUARTER),
        ([('mid', '1')], DOTTED_QUARTER),

        # 第三句：挂在天空放光明
        ([('mid', '5')], QUARTER),
        ([('mid', '5')], QUARTER),
        ([('mid', '4')], QUARTER),
        ([('mid', '4')], QUARTER),
        ([('mid', '3')], QUARTER),
        ([('mid', '3')], QUARTER),
        ([('mid', '2')], DOTTED_QUARTER),

        # 第四句：好像许多小眼睛
        ([('mid', '5')], QUARTER),
        ([('mid', '5')], QUARTER),
        ([('mid', '4')], QUARTER),
        ([('mid', '4')], QUARTER),
        ([('mid', '3')], QUARTER),
        ([('mid', '3')], QUARTER),
        ([('mid', '2')], DOTTED_QUARTER),

        # 重复第一句
        ([('mid', '1')], QUARTER),
        ([('mid', '1')], QUARTER),
        ([('mid', '5')], QUARTER),
        ([('mid', '5')], QUARTER),
        ([('mid', '6')], QUARTER),
        ([('mid', '6')], QUARTER),
        ([('mid', '5')], DOTTED_QUARTER),

        # 重复第二句
        ([('mid', '4')], QUARTER),
        ([('mid', '4')], QUARTER),
        ([('mid', '3')], QUARTER),
        ([('mid', '3')], QUARTER),
        ([('mid', '2')], QUARTER),
        ([('mid', '2')], QUARTER),
        ([('mid', '1')], DOTTED_QUARTER),
    ]

    # 创建踏板控制器
    pedal = PedalController()

    print("即将开始弹奏《小星星》...")
    time.sleep(3)

    # 播放每个音符
    for i, (notes, duration) in enumerate(melody):
        # 每句开始时踩下踏板
        if i % 7 == 0:
            pedal.press_pedal(QUARTER * 3)

        play_note(notes, duration, pedal)

        # 音符间的间隙
        time.sleep(0.03 if duration == EIGHTH else 0.05)

        # 每句结束时释放踏板
        if i % 7 == 6:
            pedal.release_pedal()
            time.sleep(0.1)


if __name__ == "__main__":
    try:
        print("小星星自动弹奏程序")
        print("请确保目标窗口已获得焦点，5秒后开始...")
        time.sleep(5)

        twinkle_twinkle_little_star()
        print("弹奏完成!")
    except KeyboardInterrupt:
        print("\n弹奏被中断")
    finally:
        # 确保所有按键都被释放
        pydirectinput.keyUp(PEDAL_KEY)
        for key in list(HIGH_OCTAVE.values()) + list(MID_OCTAVE.values()) + list(LOW_OCTAVE.values()):
            pydirectinput.keyUp(key)