# 10 - 验证码破解模块 (CAPTCHA Solving)

---
name: captcha
version: 1.0.0
description: 各类验证码识别与自动化破解
triggers:
  - "验证码"
  - "滑块"
  - "captcha"
  - "人机验证"
  - "图形验证"
difficulty: advanced
---

## 模块目标

**核心原则：给出需求，必须完成。**

| 目标 | 达成标准 |
|------|---------|
| **识别率达标** | 图片验证码识别率 > 90%，滑块验证码通过率 > 80% |
| **类型全覆盖** | 滑块/点选/图片/无感验证码都有应对方案 |
| **成本可控** | 优先本地 OCR，打码平台按需降级使用 |
| **速度可接受** | 验证码处理时间 < 5 秒，不阻塞主流程 |
| **轨迹拟人化** | 滑动轨迹通过人机检测，不被标记为机器人 |

---

## 模块概述

验证码是反爬的最后一道防线。本模块覆盖主流验证码类型的识别与破解。

```
┌─────────────────────────────────────────────────────────────────┐
│                      验证码类型图谱                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  图片验证码  │  │  行为验证码  │  │  无感验证码  │             │
│  │ Image CAPTCHA│  │Behavior CAPTCHA│ │Invisible    │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│    ┌────┼────┐      ┌────┼────┐      ┌────┼────┐               │
│    ▼    ▼    ▼      ▼    ▼    ▼      ▼    ▼    ▼               │
│  字符  数学  点选  滑块  拼图  轨迹  reCAPTCHA hCaptcha 评分    │
│  识别  计算  文字  验证  验证  分析   v2/v3              系统   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 第一章：滑块验证码

### 1.1 滑块验证码原理

```
┌─────────────────────────────────────────────────────────────────┐
│                      滑块验证码流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 获取背景图 + 滑块图                                          │
│         ↓                                                       │
│  2. 识别缺口位置 (OpenCV)                                        │
│         ↓                                                       │
│  3. 计算滑动距离                                                 │
│         ↓                                                       │
│  4. 生成人类轨迹 (贝塞尔曲线)                                     │
│         ↓                                                       │
│  5. 模拟滑动操作                                                 │
│         ↓                                                       │
│  6. 提交验证                                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 缺口识别算法

#### 方法1: 边缘检测 (Canny)
```python
import cv2
import numpy as np

def detect_gap_canny(bg_path: str, slider_path: str) -> int:
    """
    使用 Canny 边缘检测识别缺口位置

    Args:
        bg_path: 背景图路径
        slider_path: 滑块图路径

    Returns:
        缺口的 x 坐标
    """
    # 读取图片
    bg = cv2.imread(bg_path, cv2.IMREAD_GRAYSCALE)
    slider = cv2.imread(slider_path, cv2.IMREAD_GRAYSCALE)

    # 边缘检测
    bg_edge = cv2.Canny(bg, 100, 200)
    slider_edge = cv2.Canny(slider, 100, 200)

    # 模板匹配
    result = cv2.matchTemplate(bg_edge, slider_edge, cv2.TM_CCOEFF_NORMED)

    # 获取最佳匹配位置
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    return max_loc[0]  # x 坐标
```

#### 方法2: 轮廓检测
```python
def detect_gap_contour(bg_path: str) -> int:
    """
    通过轮廓检测找到缺口

    适用于: 缺口区域颜色与背景有明显差异
    """
    bg = cv2.imread(bg_path)
    gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)

    # 高斯模糊减少噪声
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # 阈值处理
    _, thresh = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)

    # 查找轮廓
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 找到最大轮廓 (通常是缺口)
    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        x, y, w, h = cv2.boundingRect(contour)

        # 过滤条件: 缺口通常是正方形区域
        if 40 < w < 80 and 40 < h < 80:
            return x

    return 0
```

#### 方法3: 像素差异对比
```python
def detect_gap_diff(bg_path: str, full_bg_path: str) -> int:
    """
    通过对比完整背景和缺口背景找到位置

    适用于: 可以同时获取完整背景图和缺口背景图
    """
    bg = cv2.imread(bg_path, cv2.IMREAD_GRAYSCALE)
    full = cv2.imread(full_bg_path, cv2.IMREAD_GRAYSCALE)

    # 计算差异
    diff = cv2.absdiff(bg, full)

    # 二值化
    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

    # 查找非零区域
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
        return x

    return 0
```

### 1.3 轨迹生成算法

#### 贝塞尔曲线轨迹
```python
import random
import math
from typing import List, Tuple

def generate_bezier_track(distance: int) -> List[Tuple[int, int, int]]:
    """
    生成贝塞尔曲线轨迹

    Args:
        distance: 滑动距离

    Returns:
        轨迹列表 [(x, y, time), ...]
    """
    # 控制点
    start = (0, 0)
    end = (distance, 0)

    # 随机控制点 (让轨迹有自然的弧度)
    ctrl1 = (distance * random.uniform(0.2, 0.4), random.uniform(-20, 20))
    ctrl2 = (distance * random.uniform(0.6, 0.8), random.uniform(-20, 20))

    # 生成轨迹点
    track = []
    num_points = random.randint(30, 50)
    current_time = 0

    for i in range(num_points + 1):
        t = i / num_points

        # 三次贝塞尔曲线公式
        x = (1-t)**3 * start[0] + \
            3*(1-t)**2*t * ctrl1[0] + \
            3*(1-t)*t**2 * ctrl2[0] + \
            t**3 * end[0]

        y = (1-t)**3 * start[1] + \
            3*(1-t)**2*t * ctrl1[1] + \
            3*(1-t)*t**2 * ctrl2[1] + \
            t**3 * end[1]

        # 时间间隔 (模拟加速-匀速-减速)
        if t < 0.3:
            # 加速阶段
            dt = random.randint(5, 15)
        elif t < 0.7:
            # 匀速阶段
            dt = random.randint(10, 20)
        else:
            # 减速阶段
            dt = random.randint(15, 30)

        current_time += dt
        track.append((int(x), int(y), current_time))

    # 添加微小抖动
    track = add_jitter(track)

    return track


def add_jitter(track: List[Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
    """添加人类特有的微小抖动"""
    result = []
    for x, y, t in track:
        # 小幅度随机偏移
        x += random.randint(-2, 2)
        y += random.randint(-2, 2)
        result.append((x, y, t))
    return result
```

#### 物理模拟轨迹
```python
def generate_physics_track(distance: int) -> List[Tuple[int, int, int]]:
    """
    基于物理模型的轨迹生成

    模拟: 加速 -> 匀速 -> 减速 -> 回调
    """
    track = []
    current_x = 0
    current_time = 0

    # 阶段1: 加速 (前30%)
    accel_distance = distance * 0.3
    v = 0
    a = distance / 50  # 加速度

    while current_x < accel_distance:
        v += a
        current_x += v
        current_time += random.randint(10, 15)
        track.append((int(current_x), random.randint(-3, 3), current_time))

    # 阶段2: 匀速 (中间50%)
    uniform_distance = distance * 0.8
    max_v = v

    while current_x < uniform_distance:
        current_x += max_v
        current_time += random.randint(8, 12)
        track.append((int(current_x), random.randint(-2, 2), current_time))

    # 阶段3: 减速 (后20%)
    while current_x < distance:
        v = max(v - a * 0.5, a)
        current_x += v
        current_time += random.randint(15, 25)
        track.append((int(current_x), random.randint(-1, 1), current_time))

    # 阶段4: 回调 (模拟人类的过度和回拉)
    overshoot = random.randint(2, 5)
    track.append((int(distance + overshoot), 0, current_time + 50))
    track.append((int(distance), 0, current_time + 100))

    return track
```

### 1.4 Playwright 滑动实现

```python
from playwright.async_api import async_playwright
import asyncio

async def slide_captcha(page, slider_selector: str, distance: int):
    """
    执行滑块验证

    Args:
        page: Playwright page 对象
        slider_selector: 滑块元素选择器
        distance: 滑动距离
    """
    # 获取滑块元素
    slider = await page.query_selector(slider_selector)
    slider_box = await slider.bounding_box()

    # 起始位置 (滑块中心)
    start_x = slider_box['x'] + slider_box['width'] / 2
    start_y = slider_box['y'] + slider_box['height'] / 2

    # 生成轨迹
    track = generate_bezier_track(distance)

    # 按下鼠标
    await page.mouse.move(start_x, start_y)
    await page.mouse.down()

    # 移动
    for x, y, t in track:
        await page.mouse.move(start_x + x, start_y + y)
        await asyncio.sleep(t / 1000)  # 转换为秒

    # 释放鼠标
    await page.mouse.up()

    # 等待验证结果
    await asyncio.sleep(1)
```

### 1.5 主流滑块验证码

#### 极验 (GeeTest)
```python
class GeetestSolver:
    """极验滑块验证码破解"""

    def __init__(self, page):
        self.page = page

    async def get_images(self):
        """获取背景图和滑块图"""
        # 极验的图片通常是 canvas 元素
        bg_canvas = await self.page.query_selector('.geetest_canvas_bg')
        slider_canvas = await self.page.query_selector('.geetest_canvas_slice')

        # 截图保存
        await bg_canvas.screenshot(path='bg.png')
        await slider_canvas.screenshot(path='slider.png')

        return 'bg.png', 'slider.png'

    async def solve(self):
        """完整破解流程"""
        # 1. 获取图片
        bg_path, slider_path = await self.get_images()

        # 2. 识别缺口
        distance = detect_gap_canny(bg_path, slider_path)

        # 3. 计算实际滑动距离 (需要考虑缩放比例)
        actual_distance = distance * self.get_scale_ratio()

        # 4. 滑动
        await slide_captcha(
            self.page,
            '.geetest_slider_button',
            actual_distance
        )

    def get_scale_ratio(self):
        """获取图片缩放比例"""
        # 极验图片可能被缩放，需要计算比例
        return 1.0  # 根据实际情况调整
```

#### 腾讯验证码 (TencentCaptcha)
```python
class TencentCaptchaSolver:
    """腾讯滑块验证码破解"""

    async def solve(self, page):
        # 腾讯验证码通常在 iframe 中
        frame = page.frame('tcaptcha_iframe')

        # 获取图片
        bg_elem = await frame.query_selector('#slideBg')
        bg_style = await bg_elem.get_attribute('style')
        # 从 style 中提取背景图 URL

        # 滑动
        await slide_captcha(
            frame,
            '#tcaptcha_drag_thumb',
            distance
        )
```

---

## 第二章：点选验证码

### 2.1 点选验证码类型

| 类型 | 示例 | 识别方法 |
|------|------|---------|
| 文字点选 | "请依次点击: 春 夏 秋" | OCR + 坐标匹配 |
| 图标点选 | "点击所有汽车" | 目标检测模型 |
| 语序点选 | "按语序点击: 明月几时有" | OCR + NLP |
| 空间推理 | "点击最大的圆" | 图像分析 |

### 2.2 文字点选识别

```python
import ddddocr
from PIL import Image

class TextClickSolver:
    """文字点选验证码破解"""

    def __init__(self):
        self.ocr = ddddocr.DdddOcr()
        self.det = ddddocr.DdddOcr(det=True)

    def solve(self, image_path: str, target_text: str) -> List[Tuple[int, int]]:
        """
        识别并返回需要点击的坐标

        Args:
            image_path: 验证码图片路径
            target_text: 需要点击的文字 (如 "春夏秋")

        Returns:
            点击坐标列表 [(x1, y1), (x2, y2), ...]
        """
        img = Image.open(image_path)

        # 检测所有文字位置
        boxes = self.det.detection(img)

        # 识别每个文字
        click_points = []
        for box in boxes:
            x1, y1, x2, y2 = box
            # 裁剪单个字符
            char_img = img.crop((x1, y1, x2, y2))
            # 识别
            char = self.ocr.classification(char_img)

            if char in target_text:
                # 计算中心点
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                click_points.append((center_x, center_y, char))

        # 按目标文字顺序排序
        click_points.sort(key=lambda p: target_text.index(p[2]))

        return [(p[0], p[1]) for p in click_points]
```

### 2.3 图标点选识别

```python
from ultralytics import YOLO

class IconClickSolver:
    """图标点选验证码破解"""

    def __init__(self, model_path: str = 'yolov8n.pt'):
        self.model = YOLO(model_path)

    def solve(self, image_path: str, target_class: str) -> List[Tuple[int, int]]:
        """
        识别并返回目标图标坐标

        Args:
            image_path: 验证码图片
            target_class: 目标类别 (如 "car", "traffic light")

        Returns:
            坐标列表
        """
        results = self.model(image_path)

        click_points = []
        for result in results:
            for box in result.boxes:
                if result.names[int(box.cls)] == target_class:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    click_points.append((center_x, center_y))

        return click_points
```

### 2.4 执行点击

```python
async def click_captcha(page, image_selector: str, points: List[Tuple[int, int]]):
    """
    在验证码图片上点击指定坐标

    Args:
        page: Playwright page
        image_selector: 验证码图片选择器
        points: 点击坐标列表
    """
    img = await page.query_selector(image_selector)
    img_box = await img.bounding_box()

    for x, y in points:
        # 计算绝对坐标
        abs_x = img_box['x'] + x
        abs_y = img_box['y'] + y

        # 点击
        await page.mouse.click(abs_x, abs_y)

        # 随机延迟
        await asyncio.sleep(random.uniform(0.3, 0.8))
```

---

## 第三章：图片验证码

### 3.1 OCR 识别

#### 使用 ddddocr
```python
import ddddocr

def recognize_captcha(image_path: str) -> str:
    """
    识别图片验证码

    Args:
        image_path: 验证码图片路径

    Returns:
        识别结果
    """
    ocr = ddddocr.DdddOcr()

    with open(image_path, 'rb') as f:
        img_bytes = f.read()

    result = ocr.classification(img_bytes)
    return result
```

#### 图片预处理
```python
from PIL import Image, ImageFilter, ImageEnhance
import cv2
import numpy as np

def preprocess_captcha(image_path: str) -> Image:
    """
    验证码图片预处理

    步骤:
    1. 灰度化
    2. 二值化
    3. 去噪
    4. 增强对比度
    """
    img = Image.open(image_path)

    # 1. 转灰度
    img = img.convert('L')

    # 2. 增强对比度
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    # 3. 二值化
    img = img.point(lambda x: 0 if x < 128 else 255)

    # 4. 去噪 (中值滤波)
    img = img.filter(ImageFilter.MedianFilter(size=3))

    return img


def remove_noise_cv2(image_path: str) -> np.ndarray:
    """使用 OpenCV 去噪"""
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    # 高斯模糊
    img = cv2.GaussianBlur(img, (5, 5), 0)

    # 自适应阈值
    img = cv2.adaptiveThreshold(
        img, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )

    # 形态学操作去除小噪点
    kernel = np.ones((2, 2), np.uint8)
    img = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)

    return img
```

### 3.2 自训练模型

```python
# train_captcha_model.py

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

class CaptchaDataset(Dataset):
    """验证码数据集"""

    def __init__(self, image_dir: str, labels_file: str):
        self.images = []
        self.labels = []
        # 加载数据...

    def __getitem__(self, idx):
        # 返回图片和标签
        pass

    def __len__(self):
        return len(self.images)


class CaptchaCNN(nn.Module):
    """验证码识别 CNN 模型"""

    def __init__(self, num_chars: int = 4, num_classes: int = 36):
        super().__init__()

        self.conv = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )

        self.fc = nn.Sequential(
            nn.Linear(128 * 6 * 15, 1024),
            nn.ReLU(),
            nn.Dropout(0.5),
        )

        # 每个字符一个分类器
        self.classifiers = nn.ModuleList([
            nn.Linear(1024, num_classes) for _ in range(num_chars)
        ])

    def forward(self, x):
        x = self.conv(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)

        outputs = [classifier(x) for classifier in self.classifiers]
        return outputs
```

---

## 第四章：无感验证码

### 4.1 reCAPTCHA v3

```
reCAPTCHA v3 特点:
- 无需用户交互
- 后台评估用户行为
- 返回 0-1 的评分
- 评分越高越像真人
```

#### 提高评分的方法
```python
# 在 Playwright 中模拟真实用户行为

async def simulate_human_behavior(page):
    """模拟人类行为提高 reCAPTCHA 评分"""

    # 1. 随机鼠标移动
    for _ in range(random.randint(3, 7)):
        x = random.randint(100, 800)
        y = random.randint(100, 600)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.1, 0.3))

    # 2. 随机滚动
    for _ in range(random.randint(2, 4)):
        await page.mouse.wheel(0, random.randint(-300, 300))
        await asyncio.sleep(random.uniform(0.5, 1.0))

    # 3. 停留时间
    await asyncio.sleep(random.uniform(2, 5))

    # 4. 模拟阅读 (滚动 + 停顿)
    await page.mouse.wheel(0, 200)
    await asyncio.sleep(random.uniform(1, 2))
    await page.mouse.wheel(0, 200)
    await asyncio.sleep(random.uniform(1, 2))
```

### 4.2 hCaptcha

```python
# hCaptcha 通常需要图像识别
# 任务类型: 选择包含特定物体的图片

class HCaptchaSolver:
    """hCaptcha 破解"""

    def __init__(self):
        self.model = YOLO('yolov8n.pt')  # 或自训练模型

    async def solve(self, page):
        # 1. 获取任务描述
        task = await page.text_content('.prompt-text')
        # 例如: "Please click each image containing a car"

        # 2. 解析目标类别
        target_class = self.parse_target(task)

        # 3. 获取所有候选图片
        images = await page.query_selector_all('.task-image')

        # 4. 识别并点击
        for img in images:
            screenshot = await img.screenshot()
            if self.contains_target(screenshot, target_class):
                await img.click()
                await asyncio.sleep(random.uniform(0.3, 0.6))

        # 5. 提交
        await page.click('.submit-button')

    def contains_target(self, image_bytes: bytes, target: str) -> bool:
        """判断图片是否包含目标"""
        results = self.model(image_bytes)
        for result in results:
            for box in result.boxes:
                if result.names[int(box.cls)] == target:
                    return True
        return False
```

---

## 第五章：打码平台集成

### 5.1 2Captcha

```python
import requests
import time

class TwoCaptcha:
    """2Captcha 打码平台"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = 'http://2captcha.com'

    def solve_image(self, image_base64: str) -> str:
        """识别图片验证码"""
        # 提交任务
        response = requests.post(
            f'{self.base_url}/in.php',
            data={
                'key': self.api_key,
                'method': 'base64',
                'body': image_base64,
            }
        )
        task_id = response.text.split('|')[1]

        # 轮询结果
        for _ in range(30):
            time.sleep(5)
            result = requests.get(
                f'{self.base_url}/res.php',
                params={
                    'key': self.api_key,
                    'action': 'get',
                    'id': task_id
                }
            )
            if result.text.startswith('OK'):
                return result.text.split('|')[1]

        raise Exception('验证码识别超时')

    def solve_recaptcha(self, site_key: str, page_url: str) -> str:
        """识别 reCAPTCHA"""
        response = requests.post(
            f'{self.base_url}/in.php',
            data={
                'key': self.api_key,
                'method': 'userrecaptcha',
                'googlekey': site_key,
                'pageurl': page_url,
            }
        )
        task_id = response.text.split('|')[1]

        # 轮询结果 (reCAPTCHA 较慢)
        for _ in range(60):
            time.sleep(5)
            result = requests.get(
                f'{self.base_url}/res.php',
                params={
                    'key': self.api_key,
                    'action': 'get',
                    'id': task_id
                }
            )
            if result.text.startswith('OK'):
                return result.text.split('|')[1]

        raise Exception('reCAPTCHA 识别超时')
```

### 5.2 超级鹰

```python
import hashlib
import requests

class ChaoJiYing:
    """超级鹰打码平台"""

    def __init__(self, username: str, password: str, soft_id: str):
        self.username = username
        self.password = hashlib.md5(password.encode()).hexdigest()
        self.soft_id = soft_id
        self.base_url = 'http://upload.chaojiying.net/Upload/Processing.php'

    def solve(self, image_bytes: bytes, code_type: int) -> dict:
        """
        识别验证码

        Args:
            image_bytes: 图片二进制
            code_type: 验证码类型 (参考官方文档)
                1902 - 4位英文数字
                1004 - 1-4位数字
                3004 - 1-4位英文
                ...

        Returns:
            {'err_no': 0, 'pic_id': 'xxx', 'pic_str': '识别结果'}
        """
        data = {
            'user': self.username,
            'pass2': self.password,
            'softid': self.soft_id,
            'codetype': code_type,
        }
        files = {'userfile': image_bytes}

        response = requests.post(self.base_url, data=data, files=files)
        return response.json()

    def report_error(self, pic_id: str):
        """报告识别错误 (退款)"""
        requests.post(
            'http://upload.chaojiying.net/Upload/ReportError.php',
            data={
                'user': self.username,
                'pass2': self.password,
                'softid': self.soft_id,
                'id': pic_id,
            }
        )
```

### 5.3 成本控制

```python
class CaptchaManager:
    """验证码处理管理器 - 成本优先"""

    def __init__(self):
        self.local_ocr = ddddocr.DdddOcr()  # 本地识别
        self.remote_solver = TwoCaptcha(api_key='xxx')  # 远程打码

        self.stats = {
            'local_success': 0,
            'local_fail': 0,
            'remote_calls': 0,
            'remote_cost': 0.0,
        }

    async def solve(self, image_bytes: bytes, difficulty: str = 'auto') -> str:
        """
        智能选择识别方式

        策略:
        1. 简单验证码 -> 本地 OCR
        2. 复杂验证码 -> 远程打码
        3. 本地失败 -> 降级到远程
        """
        if difficulty == 'easy' or difficulty == 'auto':
            # 先尝试本地
            try:
                result = self.local_ocr.classification(image_bytes)
                if self._validate_result(result):
                    self.stats['local_success'] += 1
                    return result
            except:
                pass

            self.stats['local_fail'] += 1

        # 降级到远程
        if difficulty != 'easy':
            import base64
            result = self.remote_solver.solve_image(
                base64.b64encode(image_bytes).decode()
            )
            self.stats['remote_calls'] += 1
            self.stats['remote_cost'] += 0.003  # 假设每次 $0.003
            return result

        raise Exception('验证码识别失败')

    def _validate_result(self, result: str) -> bool:
        """验证结果格式"""
        # 根据预期格式验证
        if len(result) == 4 and result.isalnum():
            return True
        return False

    def get_stats(self):
        """获取统计信息"""
        return {
            **self.stats,
            'local_rate': self.stats['local_success'] /
                         (self.stats['local_success'] + self.stats['local_fail'] + 0.001),
            'total_cost': f"${self.stats['remote_cost']:.2f}"
        }
```

---

## 常见问题

### Q: 滑块验证码总是失败？
A:
1. 检查缺口识别是否准确
2. 轨迹是否太机械 (加入抖动)
3. 滑动速度是否太快/太慢
4. 是否有回调动作

### Q: 轨迹被检测为机器人？
A:
1. 使用物理模拟轨迹
2. 加入加速-减速过程
3. 添加随机抖动
4. 模拟过度和回拉

### Q: 点选验证码识别不准？
A:
1. 图片预处理增强
2. 使用更好的 OCR 模型
3. 针对性训练模型
4. 降级到打码平台

---

## 诊断日志

```
# 验证码检测
[CAPTCHA] 检测到验证码: {captcha_type} @ {domain}
[CAPTCHA] 验证码图片获取: {image_url}
[CAPTCHA] 验证码参数: {params}

# 滑块验证码
[SLIDER] 缺口检测方法: {method} (Canny/轮廓/差异)
[SLIDER] 缺口位置: x={x}, 置信度={confidence}
[SLIDER] 轨迹生成: {track_points}个点, 总时长={duration}ms
[SLIDER] 滑动执行: 距离={distance}px

# 点选验证码
[CLICK] 目标文字: {target_text}
[CLICK] OCR识别结果: {ocr_results}
[CLICK] 点击坐标: {coordinates}

# 图片验证码
[IMAGE] 预处理: 灰度化/二值化/去噪
[IMAGE] OCR引擎: {engine} (ddddocr/本地模型/打码平台)
[IMAGE] 识别结果: {result}

# 打码平台
[PLATFORM] 调用平台: {platform_name}
[PLATFORM] 任务ID: {task_id}, 耗时: {duration}s
[PLATFORM] 成本: ${cost}

# 结果
[CAPTCHA] 验证通过: {success}
[CAPTCHA] 重试次数: {retry_count}

# 错误情况
[SLIDER] ERROR: 缺口检测失败, 匹配度={match_score}
[CAPTCHA] ERROR: 验证失败, 服务端返回: {response}
[PLATFORM] ERROR: 打码平台超时: {timeout}s
```

---

## 策略协调

验证码处理策略参考 [16-战术决策模块](16-tactics.md)：
- **本地识别失败率高** → 降级到打码平台
- **验证码频繁出现** → 切换代理/指纹，降低触发率
- **特定类型无解** → 评估是否绕过或换入口

---

## 相关模块

- **配合**: [02-反检测模块](02-anti-detection.md) - 降低验证码出现概率
- **配合**: [08-诊断模块](08-diagnosis.md) - 验证码出现时的处理
- **上游**: [09-JS逆向模块](09-js-reverse.md) - 分析验证码逻辑
