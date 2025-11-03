import warnings
# # 忽略GPU加速驱动不能用的警告(可能会忽视其他错误)
warnings.filterwarnings("ignore", category=UserWarning, message=".*pin_memory.*")
from typing import Union # 返回多个参数
import cv2
import easyocr
import win32gui
import win32con
from win32api import SetCursorPos,mouse_event,keybd_event
import win32ui
import win32clipboard
import numpy as np
import logging
import re
import time
import random
"""
结合了OCR和按键操作的类
===========================================================声明======================================================
（1）OCR需要的库：
1.OCR加速的库，根据自己显卡版本安装：pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
2.cv2库pip install opencv-python
3.easyocr库：pip install easyocr
BitBlt：内存（缓存）截图
EasyOCR：流行的OCR识别第三方库，内含识别大模型
两者结合加快识别速度
（2）鼠标键盘模拟：
============================时间定义===========================
单击：200~500毫秒时间内，按下一次
双击：200~500毫秒时间内，按下两次
长按：大于500毫秒时间外，按下一次
鼠标后摇：10~25毫秒
按键后摇:100~250毫秒
统一后摇：0~250毫秒
统一单击按下和弹起的时间延迟：300毫秒
统一双击按下和弹起的时间延迟：500毫秒
封装后所有操作在1000毫秒内实现
"""


class AutomaticSimulation:
    __hwnd = None # 窗口句柄
    # 初始化 EasyOCR 读取器,未调用GPU会报错
    __reader = easyocr.Reader(
        lang_list=['ch_sim', 'en'],  # 语言列表
        gpu=False,  # 是否使用 GPU
        # model_storage_directory='models',  # 模型存储目录
        # download_enabled=True,  # 是否自动下载模型，比如ch_sim和en
        # detector=True,  # 是否启用文本检测
        # recognizer=True,  # 是否启用文本识别
        # verbose=True  # 是否显示详细信息
    )

    def __init__(self,hwnd=None):
        """
        初始化对象，获取窗口句柄，默认前台桌面，否者无法识别
        有些游戏的窗口句柄，无法使用方法
        :param hwnd:句柄
        """
        self.__hwnd = (hwnd if hwnd else win32gui.GetDesktopWindow())

    # ===============================================================文字识别====================================================================== #

    def __capture_window(self,hwnd, top_left_region:tuple=None,bottom_left_region:tuple=None):
        """
        使用 BitBlt 捕获指定窗口或区域的屏幕截图。
        参数:
        hwnd (int): 窗口句柄。
        region (tuple): 截图区域的左上角和右下角坐标 ((left, top), (right, bottom))。
        返回:
        numpy.ndarray: 捕获的图像数据，格式为 BGR。
        """
        try:
            # 获取当前屏幕窗口尺寸
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top

            # 如果指定了区域，则调整捕获范围
            if top_left_region and bottom_left_region:
                left, top = top_left_region
                right, bottom = bottom_left_region
                width = right - left
                height = bottom - top

            # 创建设备上下文
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            # 创建位图对象
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)

            # 保存截图
            saveDC.SelectObject(saveBitMap)
            saveDC.BitBlt((0, 0), (width, height), mfcDC, (left, top), win32con.SRCCOPY)

            # 转换为 numpy 数组，图片二值化->调整颜色通道（BGRA → RGB）。
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            timg = np.frombuffer(bmpstr, dtype='uint8')
            timg = timg.reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))

            # 释放资源
            win32gui.DeleteObject(saveBitMap.GetHandle())  # 释放位图
            saveDC.DeleteDC()  # 释放保存的设备上下文
            mfcDC.DeleteDC()  # 释放窗口
            win32gui.ReleaseDC(hwnd, hwndDC)#释放临时的设备上下文

            return cv2.cvtColor(timg, cv2.COLOR_BGRA2RGB)
        except Exception as e:
            logging.error(f"捕获窗口时发生错误: {e}")
            return None

    def recognize_char(self,top_left_region:tuple=None,bottom_left_region:tuple=None,threshold=0.)->list:
        """
        识别屏幕指定区域,返回文字和位置
        :param top_left_region: 截图区域的左上角坐标
        :param bottom_left_region: 截图区域的右下角坐标
        :param threshold: 相似度=置信度,默认文字识别0.3以上，扫不到调低
        :return: [是否有文字,文本,区域坐标]格式：[布尔值,文本, ((x1, y1), (x2, y2))]
        """
        try:
            # -------------------------------使用BitBlt技术--------------------------------- #
            # 捕获指定区域图像
            img = self.__capture_window(self.__hwnd, top_left_region, bottom_left_region)
            if img is None:
                logging.error("capture_window异常未能捕获图像")
                return []

            # ---------------------------------执行OCR识别--------------------------------- #
            results = self.__reader.readtext(img)

            # 成功了返回列表，失败了返回空列表[([坐标1],[文本1],[置信度1]),([坐标2],[文本2],[置信度2]),.....]
            if not results or results[0][2] < threshold:
                return []
            # 识别到文字，返回的pos是一个元组，要转类型解析，返回列表推导：[[True,text, ((x1, y1), (x2, y2))],[True,text, ((x1, y1), (x2, y2))],...] 格式
            return [[
                text,
                (
                    (top_left_region[0] + int(pos[0][0]), top_left_region[1] + int(pos[0][1])),
                    (bottom_left_region[0] + int(pos[1][0]), bottom_left_region[1] + int(pos[1][1]))
                )]
                for (pos, text, prob) in results
                if prob >= threshold
            ]
        except Exception as e:
            logging.error(f"recognize_char发生错误: {e}")
            return []

    def match_char(self,top_left_region:tuple=None,bottom_left_region:tuple=None,match_char: str="",threshold=0.3,func=None, *args, **kwargs)->bool:
        """
        1.检测指定区域的文字是否匹配，返回列表
        2.默认采用正则匹配，匹配文本可以用正则表达,单向匹配直接写文字，多个匹配加“|”(可以改成：子字符串匹配)
        3.检测成功后可以调用传入的回调函数
        4.建议调用10毫秒检测一次（10ms/帧，FPS外挂专用）
        5.不重用recognize_char再次遍历匹配增加运行负担
        :param top_left_region: 截图区域的左上角坐标
        :param bottom_left_region: 截图区域的左上角坐标
        :param match_char: 匹配的字符串
        :param threshold: 相似度=置信度默认0.3,因为文字识别都是0.3左右，扫不到调0
        :param func: 回调函数
        :param args: 回调函数的参数
        :param kwargs: 回调函数的参数
        :return:
        """
        try:
            # -------------------------------使用BitBlt技术--------------------------------- #
            # 捕获指定区域图像
            img = self.__capture_window(self.__hwnd, top_left_region=top_left_region, bottom_left_region=bottom_left_region)
            if img is None:
                logging.error("capture_window异常未能捕获图像")
                return False

            # ------------------------------匹配字符串------------------------------------ #
            results = self.__reader.readtext(img)#执行OCR识别
            # 异常或者检测不到直接返回假
            if not results:
                return False

            # 识别到文字，返回的pos是一个元组，要转类型解析，返回列表推导：[[True,text, ((x1, y1), (x2, y2))],[True,text, ((x1, y1), (x2, y2))],...] 格式
            for (pos, text, prob) in results:
                # set(match_char) & set(text)全匹配
                if prob >= threshold and match_char and re.search(match_char, text):
                    if func:
                        func(*args, **kwargs)
                    return True

            # 以上步骤都不行情况,输出结果返回假
            print("匹配失败:\n",results)
            return False
        except Exception as e:
            logging.error(f"recognize_char发生错误: {e}")
            return False

    # ===============================================================颜色识别====================================================================== #
    def get_pixel_color(self, x:int, y:int, color_x16:str, ScreenCoordinates=True)->Union[str, bool, None]:
        """
        指定窗口坐标->像素颜色/指定窗口坐标+颜色->布尔
        :param x: 目标像素的 X 坐标（相对于窗口的客户端区域）
        :param y: 目标像素的 Y 坐标（相对于窗口的客户端区域）
        :param color_x16: 用于比较的 16 进制颜色值（可选，字符串格式）
        :param ScreenCoordinates: 是否使用屏幕坐标
        :return: RGB 颜色值 (R, G, B) 或布尔值
        """
        # 获取窗口的设备上下文 (DC)
        hdc = win32gui.GetDC(0 if ScreenCoordinates else self.__hwnd)
        if hdc == 0:
            raise ValueError("无法获取窗口设备上下文")
        try:
            # 找到的颜色
            color = win32gui.GetPixel(hdc, x, y)
            # 将颜色值转换为 RGB 格式
            r = (color & 0x00ff0000) >> 16
            g = (color & 0x0000ff00) >> 8
            b = color & 0x000000ff
            # 再将RGB转换位16进制
            hex_color = f"#{r:02X}{g:02X}{b:02X}"
            # 如果对比颜色，返回bool值。如果找色，返回字符串的16进制颜色
            if color_x16:
                return hex_color.strip('#') == color_x16
            else:
                return hex_color.strip('#') # 返回16进制的颜色，去掉#
        except Exception as e:
            print(f"报错：{e}")
            return None
        finally:
            # 无论如何都要释放设备上下文
            win32gui.ReleaseDC(self.__hwnd, hdc)

    def get_three_pixel_color(self, x1:int, y1:int, color1:str, x2:int, y2:int, color2:str, x3:int, y3:int, color3:str, ScreenCoordinates=True):
        """
        本质是 get_pixel_color 的三点取色，用于同时检测三个像素点是否匹配对应的颜色。
        :param x1: 第一个像素点的 X 坐标
        :param y1: 第一个像素点的 Y 坐标
        :param color1: 第一个像素点预期的 16 进制颜色值（字符串格式）
        :param x2: 第二个像素点的 X 坐标
        :param y2: 第二个像素点的 Y 坐标
        :param color2: 第二个像素点预期的 16 进制颜色值（字符串格式）
        :param x3: 第三个像素点的 X 坐标
        :param y3: 第三个像素点的 Y 坐标
        :param color3: 第三个像素点预期的 16 进制颜色值（字符串格式）
        :param ScreenCoordinates: 是否使用屏幕坐标，默认为 True
        :return: 如果三个点都匹配成功返回 True，否则返回 False
        """
        result1 = self.get_pixel_color(x1, y1, color1, ScreenCoordinates=ScreenCoordinates)
        result2 = self.get_pixel_color(x2, y2, color2, ScreenCoordinates=ScreenCoordinates)
        result3 = self.get_pixel_color(x3, y3, color3, ScreenCoordinates=ScreenCoordinates)
        if result1 and result2 and result3:
            return True
        else:
            print(result1, result2, result3)
            return False

    def get_area_color(self, x1:int, y1:int, x2:int, y2:int, color_x16:str, similarity_threshold=0.9, ScreenCoordinates=True):
        """
        在指定区域内查找特定颜色范围的像素
        :param x1: 区域的左上角 X 坐标
        :param y1: 区域的左上角 Y 坐标
        :param x2: 区域的右下角 X 坐标
        :param y2: 区域的右下角 Y 坐标
        :param color_x16: 目标颜色的 16 进制值（字符串格式）
        :param similarity_threshold: 相似度阈值（0 到 1 之间）
        :param ScreenCoordinates: 是否使用屏幕坐标
        :return: 找到的颜色坐标列表
        """
        target_color = tuple(int(("#"+color_x16)[i:i + 2], 16) for i in (1, 3, 5))#将16进制转换RGB
        found_positions = []
        for x in range(x1, x2 + 1):
            for y in range(y1, y2 + 1):
                pixel_color_x16 = self.get_pixel_color(x, y, ScreenCoordinates=ScreenCoordinates)
                pixel_color = tuple(int(("#" + pixel_color_x16)[i:i + 2], 16) for i in (1, 3, 5))  # 将16进制转换RGB
                if pixel_color is None:
                    continue  # 如果 get_pixel_color 返回 None，跳过当前循环
                if isinstance(pixel_color, bool):
                    continue  # 如果 get_pixel_color 返回布尔值，跳过当前循环
                r_diff = pixel_color[0] - target_color[0]
                g_diff = pixel_color[1] - target_color[1]
                b_diff = pixel_color[2] - target_color[2]
                distance = math.sqrt(r_diff ** 2 + g_diff ** 2 + b_diff ** 2)
                max_distance = math.sqrt(3 * (255 ** 2))
                similarity = 1 - (distance / max_distance)
                if similarity >= similarity_threshold:
                    found_positions.append((x, y))
        return found_positions

    """======================================================鼠标模拟============================================================"""

    def random_delay(self, delay:float=50, cooldown:float=50):
        """
        :param delay: （按下和弹起之间的）延迟时间,50比较好，200是电脑反应慢的
        :param cooldown:弹起后的延迟时间=设备反应时间/加多的随机延迟时间
        :return:None
        """
        try:
            totaldelay = (random.randint(delay, (delay + cooldown))) / 1000.0
            # sleep函数是秒级别的参数，毫米要转换成毫秒需要/1000.0
            time.sleep(totaldelay)
        except Exception as e:
            print(f"报错：{e}")

    def mouse_once_click(self, x:int, y:int, mouse_style:int=2,delay:float=50, cooldown:float=50):
        """
        模拟鼠标单击操作（左键按下并释放）。
        :param x: 鼠标点击位置的 X 坐标
        :param y: 鼠标点击位置的 Y 坐标
        :param mouse_style: 鼠标点击方式
        :param delay: （按下和弹起之间的）延迟时间,50比较好，200是电脑反应慢的
        :param cooldown:弹起后的延迟时间=设备反应时间/加多的随机延迟时间
        :return:None
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y
            win32con.MOUSEEVENTF_MOVE-移动:1
            win32con.MOUSEEVENTF_ABSOLUTE-屏幕为绝对坐标系:32768

            win32con.MOUSEEVENTF_LEFTDOWN-左键按下:2
            win32con.MOUSEEVENTF_LEFTUP-左键释放:4

            win32con.MOUSEEVENTF_RIGHTDOWN-右键按下:8
            win32con.MOUSEEVENTF_RIGHTUP-右键释放:16

            win32con.MOUSEEVENTF_MIDDLEDOWN-中键按下:32
            win32con.MOUSEEVENTF_MIDDLEUP-中键释放:64
        """
        # mouse_event(1 | 32768, x, y, 0, 0)  # 鼠标绝对移动,用不了
        SetCursorPos((x, y))  # 可以用这个代替
        self.random_delay()  # 随机延迟
        mouse_event(mouse_style, 0, 0, 0, 0)  # 按下鼠标
        self.random_delay()  # 随机延迟，小于300毫秒
        mouse_event(mouse_style * 2, 0, 0, 0, 0)  # 释放鼠标
        self.random_delay(delay, cooldown)  # 后摇时间

    def mouse_many_click(self, x:int, y:int, mouse_style:int=2, times:int=2, delay:float=100, cooldown:float=10):
        """
        模拟鼠标单击操作（左键按下并释放）。
        :param x: 鼠标点击位置的 X 坐标
        :param y: 鼠标点击位置的 Y 坐标
        :param mouse_style: 鼠标点击方式
        :param times: 点击次数
        :param delay:（按下和弹起之间的）延迟时间,50比较好，200是电脑反应慢的
        :param cooldown:弹起后的延迟时间=设备反应时间/加多的随机延迟时间
        :return:None
        win32con.MOUSEEVENTF_MOVE-移动:1
        win32con.MOUSEEVENTF_ABSOLUTE-屏幕为绝对坐标系:32768

        win32con.MOUSEEVENTF_LEFTDOWN-左键按下:2
        win32con.MOUSEEVENTF_LEFTUP-左键释放:4

        win32con.MOUSEEVENTF_RIGHTDOWN-右键按下:8
        win32con.MOUSEEVENTF_RIGHTUP-右键释放:16

        win32con.MOUSEEVENTF_MIDDLEDOWN-中键按下:32
        win32con.MOUSEEVENTF_MIDDLEUP-中键释放:64
        :param Delay:必定延迟时间
        :param Cooldown:随机延迟时间
       """
        for i in range(times):
            # mouse_event(1 | 32768, x, y, 0, 0)  # 鼠标绝对移动，用不了
            SetCursorPos((x, y))  # 可以用这个代替
            self.random_delay()  # 随机延迟
            mouse_event(mouse_style, 0, 0, 0, 0)  # 按下鼠标
            self.random_delay()  # 随机延迟，小于300毫秒
            mouse_event(mouse_style * 2, 0, 0, 0, 0)  # 释放鼠标
            self.random_delay(delay, cooldown)  # 后摇时间

    def mouse_longdown_click(self, x:int, y:int, mouse_style:int=2, delay:float=1000):
        """
        模拟鼠标单击操作（左键按下并释放）。
        :param x: 鼠标点击位置的 X 坐标
        :param y: 鼠标点击位置的 Y 坐标
        :param mouse_style: 鼠标点击方式
        :param delay:（按下和弹起之间的）延迟时间,50比较好，200是电脑反应慢的
        :return:None
        win32con.MOUSEEVENTF_MOVE-移动:1
        win32con.MOUSEEVENTF_ABSOLUTE-屏幕为绝对坐标系:32768

        win32con.MOUSEEVENTF_LEFTDOWN-左键按下:2
        win32con.MOUSEEVENTF_LEFTUP-左键释放:4

        win32con.MOUSEEVENTF_RIGHTDOWN-右键按下:8
        win32con.MOUSEEVENTF_RIGHTUP-右键释放:16

        win32con.MOUSEEVENTF_MIDDLEDOWN-中键按下:32
        win32con.MOUSEEVENTF_MIDDLEUP-中键释放:64
        :param Delay:必定延迟时间
        :param Cooldown:随机延迟时间
       """
        mouse_event(1 | 32768, x, y, 0, 0)  # 鼠标绝对移动
        self.random_delay(200, 50)  # 随机延迟
        mouse_event(mouse_style, 0, 0, 0, 0)  # 按下鼠标
        self.random_delay(delay, 0)  # 随机延迟，小于500毫秒
        mouse_event(mouse_style * 2, 0, 0, 0, 0)  # 释放鼠标
        # SetCursorPos(x,y)#可以用这个代替
        self.random_delay(200, 50)  # 后摇时间

    def mouse_wheel(self, times:int, up:bool=False, delay:float=50,cooldown:float=200):
        """
        鼠标滚轮模拟，默认一次120滚轮量。滚轮和每次滚轮的时间有关系，和次数有关系，和后摇有关系
        :param times: 滚轮次数
        :param up: 默认向上滚轮关闭
        :param delay: 每次滚轮间的延迟
        :param cooldown: 每次滚轮结束后的延迟
        """
        for i in range(times):
            mouse_event(2048, 0, 0, (120 if up else -120), 0)
            time.sleep(delay/1000)# 鸣潮会反应不过来
        time.sleep(cooldown/1000)

    def mouse_perspective_move(self, move_x:int, move_y:int, move_time:int):
        """
        鼠标相对移动
        :param move_x:水平视角一次移动的大小
        :param move_y:垂直视角一次移动的大小
        :param move_time:移动的次数
        :return:None
        """
        for i in range(move_time):
            mouse_event(1, move_x, move_y, 0, 0)
            self.random_delay(5, 10)

    """====================================================键盘模拟============================================================"""

    def key_down_times(self, vk_code: int | str, times:int=1, delay:float=50, cooldown:float=50):
        """
        使用扫描码模拟按键操作更隐蔽
        以下是常见的游戏的按键码：
        "A"	65
        "W"	87
        "D"	68
        "S"	83
        "R"	82
        "Enter"   13
     "baskspace"  8,删除
        "Ctrl"    17
        "Shift"   16
        "Esc"     27
        "Delete"  127,执行不了，其他库也一样
        "F1-F5"   112-116
        :param vk_code: 虚拟键码,字符型转整型
        :param times:按键次数，默认一次
        :param delay:（按下和弹起之间的）延迟时间,50比较好，200是电脑反应慢的
        :param cooldown:弹起后的延迟时间=设备反应时间/加多的随机延迟时间

        """
        for i in range(times):
            vk_code = ord(vk_code.upper()) if isinstance(vk_code, str) else vk_code
            keybd_event(vk_code, 0, 0, 0)  # 按下
            self.random_delay(0, 50)  # 模拟按键按下后的延迟
            keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)  # 释放
            self.random_delay(delay, cooldown)  # 模拟按键释放后的延迟

    def key_down_long(self, vk_code: int | str, delaytime:float=1000):
        """
        使用扫描码模拟按键操作
        win32con.KEYEVENTF_KEYUP-按下:2
        :param vk_code: 虚拟键码
        :param delaytime: 按下持续的时间
        """
        vk_code = ord(vk_code.upper()) if isinstance(vk_code, str) else vk_code
        keybd_event(vk_code, 0, 0, 0)  # 按下
        self.random_delay(delaytime, 0)  # 模拟按键按下后的延迟
        keybd_event(vk_code, 0, 2, 0)  # 释放
        self.random_delay()  # 模拟按键释放后的延迟

    def MessageCV(self, text:str):
        """
        讲内容写进剪辑板
        :param text: 内容
        :return: None
        """
        # 打开剪贴板
        win32clipboard.OpenClipboard()
        # 清空剪贴板
        win32clipboard.EmptyClipboard()
        # 设置文本
        win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
        # 关闭剪贴板
        win32clipboard.CloseClipboard()
        # 模拟Ctrl+V粘贴
        keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        keybd_event(ord('V'), 0, 0, 0)
        time.sleep(0.05)
        keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
        keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)

if __name__ == "__main__":
    ocrcharrecong = AutomaticSimulation()
    # 识别屏幕特定区域(左,上,右,下)
    while True:
        time.sleep(1)
        print("开始检测")
        # print(ocrcharrecong.recognize_char((1448,32), (1562,82)))
        # print(ocrcharrecong.match_char((1448,32), (1562,82),"声骸", 0.3))
        ocrcharrecong.mouse_once_click(500,500)






