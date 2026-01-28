"""
验证码识别模块 (CAPTCHA Solving Module)

功能:
- 多种验证码类型识别 (图形/滑块/点选/旋转/拼图)
- 内置识别器 (ddddocr/OpenCV/边缘检测)
- 第三方平台集成 (2captcha/超级鹰)
- 轨迹生成与模拟人类行为
- 图片预处理与增强

错误码: E_CAPTCHA_001 ~ E_CAPTCHA_006
"""

import asyncio
import hashlib
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 错误码定义
# ============================================================================

class CaptchaError(Exception):
    """验证码错误基类"""
    def __init__(self, code: str, message: str, details: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


# 错误码
E_CAPTCHA_001 = "E_CAPTCHA_001"  # 验证码类型不支持
E_CAPTCHA_002 = "E_CAPTCHA_002"  # 识别失败
E_CAPTCHA_003 = "E_CAPTCHA_003"  # 图片加载失败
E_CAPTCHA_004 = "E_CAPTCHA_004"  # 第三方平台错误
E_CAPTCHA_005 = "E_CAPTCHA_005"  # 轨迹生成失败
E_CAPTCHA_006 = "E_CAPTCHA_006"  # 配置错误


# ============================================================================
# 枚举和数据类
# ============================================================================

class CaptchaType(Enum):
    """验证码类型"""
    TEXT = "text"              # 图形验证码
    SLIDER = "slider"          # 滑块验证码
    CLICK = "click"            # 点选验证码
    ROTATE = "rotate"          # 旋转验证码
    PUZZLE = "puzzle"          # 拼图验证码
    RECAPTCHA = "recaptcha"    # Google reCAPTCHA
    HCAPTCHA = "hcaptcha"      # hCaptcha
    UNKNOWN = "unknown"        # 未知类型


@dataclass
class CaptchaResult:
    """验证码识别结果"""
    success: bool
    captcha_type: CaptchaType
    result: Union[str, dict, List[Tuple[int, int]]]  # 文本/坐标/轨迹
    confidence: float  # 置信度 0-1
    method: str  # 识别方法
    cost_time_ms: float  # 耗时(毫秒)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        status = "成功" if self.success else "失败"
        return (
            f"[{status}] {self.captcha_type.value} | "
            f"方法: {self.method} | "
            f"置信度: {self.confidence:.2%} | "
            f"耗时: {self.cost_time_ms:.1f}ms"
        )


@dataclass
class SliderTrack:
    """滑块轨迹"""
    points: List[Tuple[int, int, int]]  # [(x, y, time), ...]
    distance: int  # 总距离
    duration_ms: int  # 总时长
    algorithm: str  # 算法类型


# ============================================================================
# 验证码识别器基类
# ============================================================================

class CaptchaRecognizer(ABC):
    """验证码识别器基类"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def recognize(self, image: Union[bytes, str, Path]) -> CaptchaResult:
        """
        识别验证码

        Args:
            image: 图片 (字节/路径/Path对象)

        Returns:
            识别结果
        """
        pass

    def _load_image(self, image: Union[bytes, str, Path]) -> bytes:
        """加载图片"""
        if isinstance(image, bytes):
            return image
        elif isinstance(image, (str, Path)):
            path = Path(image)
            if not path.exists():
                raise CaptchaError(
                    E_CAPTCHA_003,
                    f"图片文件不存在: {path}",
                    {"path": str(path)}
                )
            return path.read_bytes()
        else:
            raise CaptchaError(
                E_CAPTCHA_003,
                f"不支持的图片类型: {type(image)}",
                {"type": str(type(image))}
            )


# ============================================================================
# 图形验证码识别器
# ============================================================================

class DDDOCRRecognizer(CaptchaRecognizer):
    """使用 ddddocr 识别图形验证码"""

    def __init__(self):
        super().__init__("ddddocr")
        self.ocr = None
        self._init_ocr()

    def _init_ocr(self):
        """初始化 OCR 引擎"""
        try:
            import ddddocr
            self.ocr = ddddocr.DdddOcr(show_ad=False)
            logger.info("[CAPTCHA] ddddocr 初始化成功")
        except ImportError:
            logger.warning("[CAPTCHA] ddddocr 未安装，请执行: pip install ddddocr")
            self.ocr = None
        except Exception as e:
            logger.error(f"[CAPTCHA] ddddocr 初始化失败: {e}")
            self.ocr = None

    def recognize(self, image: Union[bytes, str, Path]) -> CaptchaResult:
        """识别图形验证码"""
        start_time = time.time()

        if self.ocr is None:
            return CaptchaResult(
                success=False,
                captcha_type=CaptchaType.TEXT,
                result="",
                confidence=0.0,
                method="ddddocr",
                cost_time_ms=0,
                errors=["ddddocr 未初始化"]
            )

        try:
            # 加载图片
            image_bytes = self._load_image(image)

            # 识别
            result = self.ocr.classification(image_bytes)

            cost_time = (time.time() - start_time) * 1000

            logger.info(f"[CAPTCHA] 识别成功: {result} (耗时: {cost_time:.1f}ms)")

            return CaptchaResult(
                success=True,
                captcha_type=CaptchaType.TEXT,
                result=result,
                confidence=0.8,  # ddddocr 不提供置信度，默认0.8
                method="ddddocr",
                cost_time_ms=cost_time
            )

        except Exception as e:
            cost_time = (time.time() - start_time) * 1000
            logger.error(f"[CAPTCHA] 识别失败: {e}")
            return CaptchaResult(
                success=False,
                captcha_type=CaptchaType.TEXT,
                result="",
                confidence=0.0,
                method="ddddocr",
                cost_time_ms=cost_time,
                errors=[str(e)]
            )


# ============================================================================
# 滑块验证码识别器
# ============================================================================

class SliderRecognizer(CaptchaRecognizer):
    """滑块验证码识别器 (基于边缘检测)"""

    def __init__(self):
        super().__init__("slider")
        self.cv2 = None
        self.np = None
        self._init_cv2()

    def _init_cv2(self):
        """初始化 OpenCV"""
        try:
            import cv2
            import numpy as np
            self.cv2 = cv2
            self.np = np
            logger.info("[CAPTCHA] OpenCV 初始化成功")
        except ImportError:
            logger.warning("[CAPTCHA] OpenCV 未安装，请执行: pip install opencv-python")
            self.cv2 = None
            self.np = None

    def recognize(
        self,
        image: Union[bytes, str, Path],
        slider_image: Union[bytes, str, Path] = None,
        method: str = "auto"
    ) -> CaptchaResult:
        """
        识别滑块缺口位置

        Args:
            image: 背景图 (字节/路径/Path对象)
            slider_image: 滑块图 (可选，如果提供则使用模板匹配)
            method: 识别方法 - "auto"/"canny"/"contour"/"template"

        Returns:
            CaptchaResult，result字段为 {"gap_x": x坐标, "confidence": 置信度}
        """
        start_time = time.time()

        if self.cv2 is None:
            return CaptchaResult(
                success=False,
                captcha_type=CaptchaType.SLIDER,
                result={"gap_x": 0},
                confidence=0.0,
                method="canny",
                cost_time_ms=0,
                errors=["OpenCV 未初始化"]
            )

        try:
            # 加载背景图
            bg_bytes = self._load_image(image)
            bg_img = self.cv2.imdecode(
                self.np.frombuffer(bg_bytes, self.np.uint8),
                self.cv2.IMREAD_COLOR
            )

            if bg_img is None:
                raise CaptchaError(E_CAPTCHA_003, "无法解码背景图片")

            # 根据是否有滑块图选择识别方法
            if slider_image is not None:
                # 双图模板匹配
                slider_bytes = self._load_image(slider_image)
                gap_x, confidence = self._detect_with_template(bg_bytes, slider_bytes)
                used_method = "template"
            else:
                # 单图自动检测
                if method == "auto" or method == "canny":
                    gap_x, confidence = self._detect_gap_single_canny(bg_img)
                    used_method = "canny"
                elif method == "contour":
                    gap_x, confidence = self._detect_gap_contour(bg_img)
                    used_method = "contour"
                else:
                    gap_x, confidence = self._detect_gap_single_canny(bg_img)
                    used_method = "canny"

            cost_time = (time.time() - start_time) * 1000

            if gap_x > 0:
                logger.info(f"[CAPTCHA] 滑块缺口位置: x={gap_x}, 置信度={confidence:.2f} (耗时: {cost_time:.1f}ms)")
                return CaptchaResult(
                    success=True,
                    captcha_type=CaptchaType.SLIDER,
                    result={"gap_x": gap_x, "confidence": confidence},
                    confidence=confidence,
                    method=used_method,
                    cost_time_ms=cost_time
                )
            else:
                return CaptchaResult(
                    success=False,
                    captcha_type=CaptchaType.SLIDER,
                    result={"gap_x": 0},
                    confidence=0.0,
                    method=used_method,
                    cost_time_ms=cost_time,
                    errors=["未能检测到有效缺口位置"]
                )

        except CaptchaError as e:
            cost_time = (time.time() - start_time) * 1000
            return CaptchaResult(
                success=False,
                captcha_type=CaptchaType.SLIDER,
                result={"gap_x": 0},
                confidence=0.0,
                method="canny",
                cost_time_ms=cost_time,
                errors=[str(e)]
            )
        except Exception as e:
            cost_time = (time.time() - start_time) * 1000
            logger.error(f"[CAPTCHA] 滑块识别异常: {e}")
            return CaptchaResult(
                success=False,
                captcha_type=CaptchaType.SLIDER,
                result={"gap_x": 0},
                confidence=0.0,
                method="canny",
                cost_time_ms=cost_time,
                errors=[str(e)]
            )

    def _detect_gap_single_canny(self, img) -> Tuple[int, float]:
        """
        单图 Canny 边缘检测法 - 检测缺口位置

        原理: 缺口区域的边缘特征明显，通过边缘检测+垂直投影找到缺口

        Args:
            img: OpenCV图像对象 (BGR)

        Returns:
            (缺口x坐标, 置信度)
        """
        # 转灰度
        gray = self.cv2.cvtColor(img, self.cv2.COLOR_BGR2GRAY)

        # 高斯模糊去噪
        blurred = self.cv2.GaussianBlur(gray, (5, 5), 0)

        # Canny边缘检测
        edges = self.cv2.Canny(blurred, 50, 150)

        # 膨胀操作，使边缘更连续
        kernel = self.np.ones((3, 3), self.np.uint8)
        dilated = self.cv2.dilate(edges, kernel, iterations=2)

        # 查找轮廓
        contours, _ = self.cv2.findContours(
            dilated, self.cv2.RETR_EXTERNAL, self.cv2.CHAIN_APPROX_SIMPLE
        )

        # 筛选可能的缺口轮廓
        img_height, img_width = gray.shape
        min_area = (img_height * 0.3) * (img_width * 0.1)  # 最小面积阈值
        max_area = (img_height * 0.9) * (img_width * 0.5)  # 最大面积阈值

        candidates = []
        for contour in contours:
            x, y, w, h = self.cv2.boundingRect(contour)
            area = w * h

            # 过滤条件: 面积合适、宽高比合适、不在最左边
            if min_area < area < max_area and 0.5 < w / h < 2.0 and x > img_width * 0.1:
                # 计算轮廓的紧凑度作为置信度参考
                contour_area = self.cv2.contourArea(contour)
                rect_area = w * h
                compactness = contour_area / rect_area if rect_area > 0 else 0
                candidates.append((x, y, w, h, compactness))

        if not candidates:
            # 退化方案: 使用垂直边缘投影
            return self._detect_gap_projection(edges, img_width)

        # 选择最可能的候选 (通常在中右位置，且紧凑度高)
        candidates.sort(key=lambda c: (c[0] / img_width, -c[4]))  # 按x位置和紧凑度排序
        best = candidates[0]

        gap_x = best[0] + best[2] // 2  # 返回缺口中心x坐标
        confidence = min(0.9, 0.5 + best[4] * 0.5)  # 基于紧凑度计算置信度

        return gap_x, confidence

    def _detect_gap_projection(self, edges, img_width: int) -> Tuple[int, float]:
        """
        垂直投影法检测缺口

        原理: 缺口区域边缘密集，投影值高

        Args:
            edges: 边缘图像
            img_width: 图像宽度

        Returns:
            (缺口x坐标, 置信度)
        """
        # 垂直投影 (按列求和)
        projection = self.np.sum(edges, axis=0)

        # 在图像中间区域寻找峰值 (排除最左边10%和最右边10%)
        start = int(img_width * 0.1)
        end = int(img_width * 0.9)
        search_region = projection[start:end]

        if len(search_region) == 0:
            return 0, 0.0

        # 找到峰值位置
        peak_idx = self.np.argmax(search_region)
        gap_x = start + peak_idx

        # 计算置信度 (基于峰值与平均值的比值)
        avg_val = self.np.mean(projection)
        peak_val = search_region[peak_idx]
        confidence = min(0.8, 0.3 + (peak_val / avg_val) * 0.1) if avg_val > 0 else 0.3

        return gap_x, confidence

    def _detect_gap_contour(self, img) -> Tuple[int, float]:
        """
        轮廓检测法 - 基于颜色差异检测缺口

        原理: 缺口区域颜色通常与背景有明显差异

        Args:
            img: OpenCV图像对象 (BGR)

        Returns:
            (缺口x坐标, 置信度)
        """
        # 转换到HSV色彩空间
        hsv = self.cv2.cvtColor(img, self.cv2.COLOR_BGR2HSV)

        # 提取亮度通道
        _, _, v = self.cv2.split(hsv)

        # 自适应阈值二值化
        binary = self.cv2.adaptiveThreshold(
            v, 255, self.cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            self.cv2.THRESH_BINARY_INV, 11, 2
        )

        # 形态学操作
        kernel = self.np.ones((5, 5), self.np.uint8)
        opened = self.cv2.morphologyEx(binary, self.cv2.MORPH_OPEN, kernel)
        closed = self.cv2.morphologyEx(opened, self.cv2.MORPH_CLOSE, kernel)

        # 查找轮廓
        contours, _ = self.cv2.findContours(
            closed, self.cv2.RETR_EXTERNAL, self.cv2.CHAIN_APPROX_SIMPLE
        )

        img_height, img_width = v.shape

        # 筛选缺口候选
        candidates = []
        for contour in contours:
            x, y, w, h = self.cv2.boundingRect(contour)
            area = w * h

            # 缺口通常是方形或近似方形
            if area > 500 and 0.6 < w / h < 1.5 and x > img_width * 0.15:
                circularity = 4 * 3.14159 * self.cv2.contourArea(contour) / (self.cv2.arcLength(contour, True) ** 2 + 1)
                candidates.append((x, w, circularity))

        if not candidates:
            # 退化到Canny方法
            return self._detect_gap_single_canny(img)

        # 选择最佳候选
        candidates.sort(key=lambda c: -c[2])  # 按圆形度排序
        best = candidates[0]
        gap_x = best[0] + best[1] // 2
        confidence = min(0.85, 0.4 + best[2] * 0.5)

        return gap_x, confidence

    def _detect_with_template(self, bg_bytes: bytes, slider_bytes: bytes) -> Tuple[int, float]:
        """
        双图模板匹配法

        Args:
            bg_bytes: 背景图字节
            slider_bytes: 滑块图字节

        Returns:
            (缺口x坐标, 置信度)
        """
        # 解码图片
        bg = self.cv2.imdecode(
            self.np.frombuffer(bg_bytes, self.np.uint8),
            self.cv2.IMREAD_GRAYSCALE
        )
        slider = self.cv2.imdecode(
            self.np.frombuffer(slider_bytes, self.np.uint8),
            self.cv2.IMREAD_GRAYSCALE
        )

        if bg is None or slider is None:
            raise CaptchaError(E_CAPTCHA_003, "无法解码图片")

        # 处理滑块图 - 移除透明/白色边缘
        _, slider_thresh = self.cv2.threshold(slider, 200, 255, self.cv2.THRESH_BINARY_INV)

        # Canny边缘检测
        bg_edge = self.cv2.Canny(bg, 100, 200)
        slider_edge = self.cv2.Canny(slider_thresh, 100, 200)

        # 确保滑块不大于背景
        if slider_edge.shape[0] > bg_edge.shape[0] or slider_edge.shape[1] > bg_edge.shape[1]:
            # 缩放滑块
            scale = min(bg_edge.shape[0] / slider_edge.shape[0], bg_edge.shape[1] / slider_edge.shape[1]) * 0.9
            new_size = (int(slider_edge.shape[1] * scale), int(slider_edge.shape[0] * scale))
            slider_edge = self.cv2.resize(slider_edge, new_size)

        # 模板匹配
        result = self.cv2.matchTemplate(
            bg_edge, slider_edge, self.cv2.TM_CCOEFF_NORMED
        )

        # 获取最佳匹配位置
        min_val, max_val, min_loc, max_loc = self.cv2.minMaxLoc(result)

        gap_x = max_loc[0]
        confidence = max(0, min(1, max_val))  # 归一化置信度

        return gap_x, confidence

    def detect_gap_canny(self, bg_image: bytes, slider_image: bytes) -> int:
        """
        使用 Canny 边缘检测识别缺口位置 (兼容旧接口)

        Args:
            bg_image: 背景图字节
            slider_image: 滑块图字节

        Returns:
            缺口的 x 坐标
        """
        if self.cv2 is None or self.np is None:
            raise CaptchaError(E_CAPTCHA_002, "OpenCV 未初始化")

        # 调用新的模板匹配实现
        gap_x, confidence = self._detect_with_template(bg_image, slider_image)
        logger.info(f"[CAPTCHA] 缺口位置: x={gap_x}, 置信度={confidence:.2f}")
        return gap_x


# ============================================================================
# 点选验证码识别器
# ============================================================================

class ClickRecognizer(CaptchaRecognizer):
    """点选验证码识别器

    支持两种模式:
    1. 文字点选: 根据提示文字，在图片中找到对应文字位置
    2. 图标点选: 识别图片中的图标位置
    """

    def __init__(self):
        super().__init__("click")
        self.ocr = None
        self.det = None
        self.cv2 = None
        self.np = None
        self._init_ocr()
        self._init_cv2()

    def _init_ocr(self):
        """初始化 OCR 引擎"""
        try:
            import ddddocr
            self.ocr = ddddocr.DdddOcr(show_ad=False)
            self.det = ddddocr.DdddOcr(det=True, show_ad=False)
            logger.info("[CAPTCHA] 点选 OCR 初始化成功")
        except ImportError:
            logger.warning("[CAPTCHA] ddddocr 未安装")
            self.ocr = None
            self.det = None

    def _init_cv2(self):
        """初始化 OpenCV"""
        try:
            import cv2
            import numpy as np
            self.cv2 = cv2
            self.np = np
        except ImportError:
            self.cv2 = None
            self.np = None

    def recognize(
        self,
        image: Union[bytes, str, Path],
        target_chars: str = None,
        target_count: int = None
    ) -> CaptchaResult:
        """
        识别点选验证码

        Args:
            image: 验证码图片
            target_chars: 目标文字 (如 "春夏秋冬"，按此顺序点击)
            target_count: 需要点击的数量 (如果没有target_chars)

        Returns:
            CaptchaResult，result字段为 [(x1,y1), (x2,y2), ...] 点击坐标列表
        """
        start_time = time.time()

        if self.det is None:
            return CaptchaResult(
                success=False,
                captcha_type=CaptchaType.CLICK,
                result=[],
                confidence=0.0,
                method="ocr_detection",
                cost_time_ms=0,
                errors=["ddddocr 目标检测模块未初始化"]
            )

        try:
            # 加载图片
            image_bytes = self._load_image(image)

            # 使用 ddddocr 检测所有文字/图标位置
            detected_boxes = self.det.detection(image_bytes)

            if not detected_boxes:
                cost_time = (time.time() - start_time) * 1000
                return CaptchaResult(
                    success=False,
                    captcha_type=CaptchaType.CLICK,
                    result=[],
                    confidence=0.0,
                    method="ocr_detection",
                    cost_time_ms=cost_time,
                    errors=["未检测到任何可点击元素"]
                )

            # 提取每个检测框的文字并记录位置
            char_positions = []
            for box in detected_boxes:
                # box 格式: [x1, y1, x2, y2]
                x1, y1, x2, y2 = box
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                # 裁剪该区域并识别文字
                if self.cv2 is not None and self.np is not None:
                    img_array = self.np.frombuffer(image_bytes, self.np.uint8)
                    img = self.cv2.imdecode(img_array, self.cv2.IMREAD_COLOR)
                    if img is not None:
                        # 裁剪文字区域
                        crop = img[int(y1):int(y2), int(x1):int(x2)]
                        _, crop_bytes = self.cv2.imencode('.png', crop)
                        crop_bytes = crop_bytes.tobytes()

                        # 识别文字
                        if self.ocr is not None:
                            try:
                                char_text = self.ocr.classification(crop_bytes)
                                char_positions.append({
                                    "char": char_text,
                                    "box": box,
                                    "center": (center_x, center_y)
                                })
                            except:
                                char_positions.append({
                                    "char": "",
                                    "box": box,
                                    "center": (center_x, center_y)
                                })
                else:
                    char_positions.append({
                        "char": "",
                        "box": box,
                        "center": (center_x, center_y)
                    })

            # 根据目标文字排序点击顺序
            click_points = []
            confidence = 0.7

            if target_chars:
                # 按目标文字顺序排列
                for target_char in target_chars:
                    for cp in char_positions:
                        if target_char in cp["char"] or cp["char"] in target_char:
                            click_points.append(cp["center"])
                            break

                # 如果没找到所有目标，使用位置推断
                if len(click_points) < len(target_chars):
                    # 尝试模糊匹配
                    remaining = [cp for cp in char_positions if cp["center"] not in click_points]
                    for cp in remaining[:len(target_chars) - len(click_points)]:
                        click_points.append(cp["center"])
                    confidence = 0.5  # 降低置信度
            else:
                # 没有目标文字，返回所有检测到的位置
                click_points = [cp["center"] for cp in char_positions]
                if target_count:
                    click_points = click_points[:target_count]

            cost_time = (time.time() - start_time) * 1000

            if click_points:
                logger.info(
                    f"[CAPTCHA] 点选识别成功: {len(click_points)}个点击位置 "
                    f"(耗时: {cost_time:.1f}ms)"
                )
                return CaptchaResult(
                    success=True,
                    captcha_type=CaptchaType.CLICK,
                    result=click_points,
                    confidence=confidence,
                    method="ocr_detection",
                    cost_time_ms=cost_time,
                    metadata={
                        "detected_count": len(char_positions),
                        "char_positions": char_positions
                    }
                )
            else:
                return CaptchaResult(
                    success=False,
                    captcha_type=CaptchaType.CLICK,
                    result=[],
                    confidence=0.0,
                    method="ocr_detection",
                    cost_time_ms=cost_time,
                    errors=["未能匹配到目标文字位置"]
                )

        except Exception as e:
            cost_time = (time.time() - start_time) * 1000
            logger.error(f"[CAPTCHA] 点选识别失败: {e}")
            return CaptchaResult(
                success=False,
                captcha_type=CaptchaType.CLICK,
                result=[],
                confidence=0.0,
                method="ocr_detection",
                cost_time_ms=cost_time,
                errors=[str(e)]
            )

    def recognize_icons(
        self,
        image: Union[bytes, str, Path],
        icon_count: int = 4
    ) -> CaptchaResult:
        """
        识别图标点选验证码

        Args:
            image: 验证码图片
            icon_count: 需要识别的图标数量

        Returns:
            CaptchaResult，result字段为图标中心坐标列表
        """
        start_time = time.time()

        if self.cv2 is None or self.np is None:
            return CaptchaResult(
                success=False,
                captcha_type=CaptchaType.CLICK,
                result=[],
                confidence=0.0,
                method="icon_detection",
                cost_time_ms=0,
                errors=["OpenCV 未初始化"]
            )

        try:
            image_bytes = self._load_image(image)
            img_array = self.np.frombuffer(image_bytes, self.np.uint8)
            img = self.cv2.imdecode(img_array, self.cv2.IMREAD_COLOR)

            if img is None:
                raise CaptchaError(E_CAPTCHA_003, "无法解码图片")

            # 转灰度
            gray = self.cv2.cvtColor(img, self.cv2.COLOR_BGR2GRAY)

            # 二值化
            _, binary = self.cv2.threshold(gray, 0, 255, self.cv2.THRESH_BINARY_INV + self.cv2.THRESH_OTSU)

            # 查找轮廓
            contours, _ = self.cv2.findContours(binary, self.cv2.RETR_EXTERNAL, self.cv2.CHAIN_APPROX_SIMPLE)

            # 筛选合适大小的轮廓
            img_height, img_width = gray.shape
            min_size = min(img_height, img_width) * 0.05
            max_size = min(img_height, img_width) * 0.4

            icons = []
            for contour in contours:
                x, y, w, h = self.cv2.boundingRect(contour)
                if min_size < w < max_size and min_size < h < max_size:
                    center_x = x + w // 2
                    center_y = y + h // 2
                    area = w * h
                    icons.append({
                        "center": (center_x, center_y),
                        "box": (x, y, w, h),
                        "area": area
                    })

            # 按面积排序，取前N个
            icons.sort(key=lambda x: -x["area"])
            icons = icons[:icon_count]

            # 按从左到右、从上到下排序
            icons.sort(key=lambda x: (x["center"][1] // 50, x["center"][0]))

            click_points = [icon["center"] for icon in icons]

            cost_time = (time.time() - start_time) * 1000

            if click_points:
                return CaptchaResult(
                    success=True,
                    captcha_type=CaptchaType.CLICK,
                    result=click_points,
                    confidence=0.7,
                    method="icon_detection",
                    cost_time_ms=cost_time
                )
            else:
                return CaptchaResult(
                    success=False,
                    captcha_type=CaptchaType.CLICK,
                    result=[],
                    confidence=0.0,
                    method="icon_detection",
                    cost_time_ms=cost_time,
                    errors=["未检测到图标"]
                )

        except Exception as e:
            cost_time = (time.time() - start_time) * 1000
            logger.error(f"[CAPTCHA] 图标检测失败: {e}")
            return CaptchaResult(
                success=False,
                captcha_type=CaptchaType.CLICK,
                result=[],
                confidence=0.0,
                method="icon_detection",
                cost_time_ms=cost_time,
                errors=[str(e)]
            )


# ============================================================================
# 第三方平台识别器
# ============================================================================

class ThirdPartyRecognizer(CaptchaRecognizer):
    """第三方打码平台识别器

    支持平台:
    - 2captcha: https://2captcha.com/
    - chaojiying (超级鹰): http://www.chaojiying.com/

    使用示例:
        # 2Captcha
        recognizer = ThirdPartyRecognizer("2captcha", api_key="your_api_key")
        result = recognizer.recognize(image_bytes)

        # 超级鹰
        recognizer = ThirdPartyRecognizer(
            "chaojiying",
            api_key="your_api_key",
            username="your_username",
            password="your_password",
            soft_id="your_soft_id"
        )
        result = recognizer.recognize(image_bytes, captcha_type="1902")
    """

    # 2Captcha API endpoints
    TWOCAPTCHA_IN_URL = "https://2captcha.com/in.php"
    TWOCAPTCHA_RES_URL = "https://2captcha.com/res.php"

    # 超级鹰 API endpoint
    CHAOJIYING_URL = "http://upload.chaojiying.net/Upload/Processing.php"

    def __init__(self, platform: str, api_key: str, **kwargs):
        super().__init__(f"third_party_{platform}")
        self.platform = platform
        self.api_key = api_key
        self.config = kwargs

        # 超级鹰额外配置
        self.username = kwargs.get("username", "")
        self.password = kwargs.get("password", "")
        self.soft_id = kwargs.get("soft_id", "")

        # 轮询配置
        self.poll_interval = kwargs.get("poll_interval", 5)  # 秒
        self.max_wait_time = kwargs.get("max_wait_time", 120)  # 秒

    def recognize(
        self,
        image: Union[bytes, str, Path],
        captcha_type: str = None
    ) -> CaptchaResult:
        """
        调用第三方平台识别

        Args:
            image: 验证码图片
            captcha_type: 验证码类型代码 (平台特定)
                - 2Captcha: "normal" / "funcaptcha" / "recaptcha" 等
                - 超级鹰: "1902" (数字) / "1004" (字母+数字) 等

        Returns:
            识别结果
        """
        if self.platform == "2captcha":
            return self._call_2captcha(image, captcha_type)
        elif self.platform == "chaojiying":
            return self._call_chaojiying(image, captcha_type)
        else:
            return CaptchaResult(
                success=False,
                captcha_type=CaptchaType.UNKNOWN,
                result="",
                confidence=0.0,
                method=self.platform,
                cost_time_ms=0,
                errors=[f"不支持的平台: {self.platform}"]
            )

    def _call_2captcha(
        self,
        image: Union[bytes, str, Path],
        captcha_type: str = None
    ) -> CaptchaResult:
        """
        调用 2Captcha API

        流程:
        1. 上传图片到 in.php
        2. 轮询 res.php 获取结果
        """
        start_time = time.time()

        try:
            import httpx
            import base64
        except ImportError:
            return CaptchaResult(
                success=False,
                captcha_type=CaptchaType.TEXT,
                result="",
                confidence=0.0,
                method="2captcha",
                cost_time_ms=0,
                errors=["缺少 httpx 库，请安装: pip install httpx"]
            )

        try:
            # 加载图片
            image_bytes = self._load_image(image)
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')

            # Step 1: 上传图片
            upload_data = {
                "key": self.api_key,
                "method": "base64",
                "body": image_b64,
                "json": "1"
            }

            # 添加可选参数
            if captcha_type:
                upload_data["textinstructions"] = captcha_type

            with httpx.Client(timeout=30) as client:
                upload_resp = client.post(self.TWOCAPTCHA_IN_URL, data=upload_data)
                upload_result = upload_resp.json()

                if upload_result.get("status") != 1:
                    cost_time = (time.time() - start_time) * 1000
                    return CaptchaResult(
                        success=False,
                        captcha_type=CaptchaType.TEXT,
                        result="",
                        confidence=0.0,
                        method="2captcha",
                        cost_time_ms=cost_time,
                        errors=[f"上传失败: {upload_result.get('request', 'Unknown error')}"]
                    )

                request_id = upload_result.get("request")
                logger.info(f"[2Captcha] 上传成功, request_id: {request_id}")

                # Step 2: 轮询获取结果
                poll_start = time.time()
                time.sleep(5)  # 初始等待5秒

                while time.time() - poll_start < self.max_wait_time:
                    result_resp = client.get(
                        self.TWOCAPTCHA_RES_URL,
                        params={
                            "key": self.api_key,
                            "action": "get",
                            "id": request_id,
                            "json": "1"
                        }
                    )
                    result_data = result_resp.json()

                    if result_data.get("status") == 1:
                        # 识别成功
                        captcha_text = result_data.get("request", "")
                        cost_time = (time.time() - start_time) * 1000

                        logger.info(f"[2Captcha] 识别成功: {captcha_text} (耗时: {cost_time:.1f}ms)")

                        return CaptchaResult(
                            success=True,
                            captcha_type=CaptchaType.TEXT,
                            result=captcha_text,
                            confidence=0.95,  # 第三方平台通常有人工校验
                            method="2captcha",
                            cost_time_ms=cost_time,
                            metadata={"request_id": request_id}
                        )

                    elif result_data.get("request") == "CAPCHA_NOT_READY":
                        # 还在处理中
                        logger.debug(f"[2Captcha] 等待结果...")
                        time.sleep(self.poll_interval)
                        continue
                    else:
                        # 其他错误
                        cost_time = (time.time() - start_time) * 1000
                        return CaptchaResult(
                            success=False,
                            captcha_type=CaptchaType.TEXT,
                            result="",
                            confidence=0.0,
                            method="2captcha",
                            cost_time_ms=cost_time,
                            errors=[f"识别失败: {result_data.get('request', 'Unknown error')}"]
                        )

                # 超时
                cost_time = (time.time() - start_time) * 1000
                return CaptchaResult(
                    success=False,
                    captcha_type=CaptchaType.TEXT,
                    result="",
                    confidence=0.0,
                    method="2captcha",
                    cost_time_ms=cost_time,
                    errors=[f"识别超时 ({self.max_wait_time}s)"]
                )

        except Exception as e:
            cost_time = (time.time() - start_time) * 1000
            logger.error(f"[2Captcha] API调用异常: {e}")
            return CaptchaResult(
                success=False,
                captcha_type=CaptchaType.TEXT,
                result="",
                confidence=0.0,
                method="2captcha",
                cost_time_ms=cost_time,
                errors=[str(e)]
            )

    def _call_chaojiying(
        self,
        image: Union[bytes, str, Path],
        captcha_type: str = "1902"
    ) -> CaptchaResult:
        """
        调用超级鹰 API

        验证码类型代码 (codetype):
        - 1902: 2位数字
        - 1004: 4位字母+数字
        - 1006: 6位字母+数字
        - 9004: 坐标型 (点选)
        - 更多类型参见: http://www.chaojiying.com/price.html
        """
        start_time = time.time()

        try:
            import httpx
        except ImportError:
            return CaptchaResult(
                success=False,
                captcha_type=CaptchaType.TEXT,
                result="",
                confidence=0.0,
                method="chaojiying",
                cost_time_ms=0,
                errors=["缺少 httpx 库，请安装: pip install httpx"]
            )

        # 检查必要配置
        if not self.username or not self.password:
            return CaptchaResult(
                success=False,
                captcha_type=CaptchaType.TEXT,
                result="",
                confidence=0.0,
                method="chaojiying",
                cost_time_ms=0,
                errors=["超级鹰需要 username 和 password 参数"]
            )

        try:
            # 加载图片
            image_bytes = self._load_image(image)

            # 计算密码MD5
            password_md5 = hashlib.md5(self.password.encode()).hexdigest()

            # 构造请求
            data = {
                "user": self.username,
                "pass2": password_md5,
                "softid": self.soft_id or "96001",  # 默认软件ID
                "codetype": captcha_type
            }

            files = {
                "userfile": ("captcha.jpg", image_bytes, "image/jpeg")
            }

            with httpx.Client(timeout=60) as client:
                resp = client.post(
                    self.CHAOJIYING_URL,
                    data=data,
                    files=files
                )
                result = resp.json()

                cost_time = (time.time() - start_time) * 1000

                if result.get("err_no") == 0:
                    # 识别成功
                    captcha_text = result.get("pic_str", "")

                    logger.info(f"[超级鹰] 识别成功: {captcha_text} (耗时: {cost_time:.1f}ms)")

                    # 解析结果 (坐标型返回格式: "x1,y1|x2,y2")
                    if captcha_type in ["9004", "9005", "9006", "9007"]:
                        # 坐标型验证码
                        points = []
                        for coord in captcha_text.split("|"):
                            if "," in coord:
                                x, y = coord.split(",")
                                points.append((int(x), int(y)))
                        final_result = points
                        result_type = CaptchaType.CLICK
                    else:
                        final_result = captcha_text
                        result_type = CaptchaType.TEXT

                    return CaptchaResult(
                        success=True,
                        captcha_type=result_type,
                        result=final_result,
                        confidence=0.95,
                        method="chaojiying",
                        cost_time_ms=cost_time,
                        metadata={
                            "pic_id": result.get("pic_id"),
                            "md5": result.get("md5")
                        }
                    )
                else:
                    # 识别失败
                    error_msg = result.get("err_str", f"错误码: {result.get('err_no')}")
                    logger.error(f"[超级鹰] 识别失败: {error_msg}")

                    return CaptchaResult(
                        success=False,
                        captcha_type=CaptchaType.TEXT,
                        result="",
                        confidence=0.0,
                        method="chaojiying",
                        cost_time_ms=cost_time,
                        errors=[error_msg]
                    )

        except Exception as e:
            cost_time = (time.time() - start_time) * 1000
            logger.error(f"[超级鹰] API调用异常: {e}")
            return CaptchaResult(
                success=False,
                captcha_type=CaptchaType.TEXT,
                result="",
                confidence=0.0,
                method="chaojiying",
                cost_time_ms=cost_time,
                errors=[str(e)]
            )

    def report_error(self, request_id: str) -> bool:
        """
        报告识别错误 (用于退款)

        仅 2Captcha 支持
        """
        if self.platform != "2captcha":
            logger.warning(f"[{self.platform}] 不支持错误报告")
            return False

        try:
            import httpx
            with httpx.Client(timeout=30) as client:
                resp = client.get(
                    self.TWOCAPTCHA_RES_URL,
                    params={
                        "key": self.api_key,
                        "action": "reportbad",
                        "id": request_id,
                        "json": "1"
                    }
                )
                result = resp.json()
                if result.get("status") == 1:
                    logger.info(f"[2Captcha] 错误报告成功: {request_id}")
                    return True
                else:
                    logger.warning(f"[2Captcha] 错误报告失败: {result}")
                    return False
        except Exception as e:
            logger.error(f"[2Captcha] 错误报告异常: {e}")
            return False


# ============================================================================
# 轨迹生成器
# ============================================================================

class TrajectoryGenerator:
    """轨迹生成器 - 模拟人类滑动行为"""

    @staticmethod
    def generate_bezier_track(distance: int) -> SliderTrack:
        """
        生成贝塞尔曲线轨迹

        Args:
            distance: 滑动距离(像素)

        Returns:
            滑块轨迹
        """
        # 控制点
        start = (0, 0)
        end = (distance, 0)

        # 随机控制点 (让轨迹有自然的弧度)
        ctrl1 = (
            int(distance * random.uniform(0.2, 0.4)),
            int(random.uniform(-20, 20))
        )
        ctrl2 = (
            int(distance * random.uniform(0.6, 0.8)),
            int(random.uniform(-20, 20))
        )

        # 生成轨迹点
        track = []
        num_points = random.randint(30, 50)
        current_time = 0

        for i in range(num_points + 1):
            t = i / num_points

            # 三次贝塞尔曲线公式
            x = (
                (1 - t) ** 3 * start[0] +
                3 * (1 - t) ** 2 * t * ctrl1[0] +
                3 * (1 - t) * t ** 2 * ctrl2[0] +
                t ** 3 * end[0]
            )

            y = (
                (1 - t) ** 3 * start[1] +
                3 * (1 - t) ** 2 * t * ctrl1[1] +
                3 * (1 - t) * t ** 2 * ctrl2[1] +
                t ** 3 * end[1]
            )

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
        track = TrajectoryGenerator._add_jitter(track)

        return SliderTrack(
            points=track,
            distance=distance,
            duration_ms=current_time,
            algorithm="bezier"
        )

    @staticmethod
    def generate_physics_track(distance: int) -> SliderTrack:
        """
        基于物理模型的轨迹生成

        模拟: 加速 -> 匀速 -> 减速 -> 回调

        Args:
            distance: 滑动距离

        Returns:
            滑块轨迹
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

        return SliderTrack(
            points=track,
            distance=distance,
            duration_ms=current_time + 100,
            algorithm="physics"
        )

    @staticmethod
    def _add_jitter(track: List[Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
        """添加人类特有的微小抖动"""
        result = []
        for x, y, t in track:
            # 小幅度随机偏移
            x += random.randint(-2, 2)
            y += random.randint(-2, 2)
            result.append((x, y, t))
        return result


# ============================================================================
# 验证码管理器
# ============================================================================

class CaptchaManager:
    """验证码管理器 - 统一管理多种识别器"""

    def __init__(self):
        self.recognizers: Dict[CaptchaType, List[CaptchaRecognizer]] = {}
        self.stats = {
            "total": 0,
            "success": 0,
            "failure": 0,
            "by_type": {},
            "by_method": {}
        }

    def register(
        self,
        captcha_type: CaptchaType,
        recognizer: CaptchaRecognizer,
        priority: int = 0
    ):
        """
        注册识别器

        Args:
            captcha_type: 验证码类型
            recognizer: 识别器实例
            priority: 优先级 (数字越小优先级越高)
        """
        if captcha_type not in self.recognizers:
            self.recognizers[captcha_type] = []

        self.recognizers[captcha_type].append((priority, recognizer))
        # 按优先级排序
        self.recognizers[captcha_type].sort(key=lambda x: x[0])

        logger.info(
            f"[CAPTCHA] 注册识别器: {captcha_type.value} -> {recognizer.name} "
            f"(优先级: {priority})"
        )

    def recognize(
        self,
        image: Union[bytes, str, Path],
        captcha_type: Optional[CaptchaType] = None,
        auto_detect: bool = True
    ) -> CaptchaResult:
        """
        识别验证码

        Args:
            image: 图片
            captcha_type: 验证码类型 (None则自动检测)
            auto_detect: 是否自动检测类型

        Returns:
            识别结果
        """
        self.stats["total"] += 1

        # 自动检测类型
        if captcha_type is None and auto_detect:
            captcha_type = self.auto_detect_type(image)

        if captcha_type is None:
            captcha_type = CaptchaType.UNKNOWN

        # 获取该类型的识别器
        recognizers = self.recognizers.get(captcha_type, [])

        if not recognizers:
            logger.warning(f"[CAPTCHA] 未找到 {captcha_type.value} 类型的识别器")
            result = CaptchaResult(
                success=False,
                captcha_type=captcha_type,
                result="",
                confidence=0.0,
                method="none",
                cost_time_ms=0,
                errors=[f"未找到 {captcha_type.value} 类型的识别器"]
            )
            self._record_result(result)
            return result

        # 依次尝试识别器
        for priority, recognizer in recognizers:
            logger.info(
                f"[CAPTCHA] 尝试识别: {captcha_type.value} -> {recognizer.name}"
            )
            result = recognizer.recognize(image)

            if result.success:
                logger.info(f"[CAPTCHA] 识别成功: {result}")
                self._record_result(result)
                return result
            else:
                logger.warning(f"[CAPTCHA] 识别失败: {result.errors}")

        # 所有识别器都失败
        result = CaptchaResult(
            success=False,
            captcha_type=captcha_type,
            result="",
            confidence=0.0,
            method="all_failed",
            cost_time_ms=0,
            errors=["所有识别器都失败"]
        )
        self._record_result(result)
        return result

    def auto_detect_type(self, image: Union[bytes, str, Path]) -> CaptchaType:
        """
        自动检测验证码类型

        检测策略:
        1. 分析图片尺寸 - 滑块通常宽度远大于高度
        2. 检测文字区域 - 有大量文字可能是点选
        3. 检测缺口特征 - 有明显缺口是滑块
        4. 检测提示区域 - 有"点击"提示是点选

        Returns:
            检测到的验证码类型
        """
        try:
            # 加载图片
            if isinstance(image, bytes):
                image_bytes = image
            elif isinstance(image, (str, Path)):
                path = Path(image)
                if not path.exists():
                    return CaptchaType.TEXT
                image_bytes = path.read_bytes()
            else:
                return CaptchaType.TEXT

            # 尝试使用 Pillow 分析
            try:
                from PIL import Image
                import io

                img = Image.open(io.BytesIO(image_bytes))
                width, height = img.size

                # 特征1: 宽高比分析
                aspect_ratio = width / height if height > 0 else 1

                # 滑块验证码通常宽度远大于高度 (宽高比 > 2.5)
                if aspect_ratio > 2.5:
                    logger.debug(f"[CAPTCHA] 宽高比 {aspect_ratio:.2f}，判断为滑块验证码")
                    return CaptchaType.SLIDER

                # 特征2: 尺寸分析
                # 小图片 (如 100x40) 通常是简单文字验证码
                if width < 150 and height < 60:
                    logger.debug(f"[CAPTCHA] 尺寸 {width}x{height}，判断为文字验证码")
                    return CaptchaType.TEXT

                # 特征3: 大图片可能是点选验证码
                if width > 300 and height > 200:
                    # 进一步分析：检测是否有多个独立区域
                    try:
                        import cv2
                        import numpy as np

                        img_array = np.frombuffer(image_bytes, np.uint8)
                        cv_img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)

                        if cv_img is not None:
                            # 边缘检测
                            edges = cv2.Canny(cv_img, 50, 150)

                            # 查找轮廓
                            contours, _ = cv2.findContours(
                                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                            )

                            # 过滤小轮廓，统计大轮廓数量
                            min_area = (width * height) * 0.01  # 至少1%面积
                            significant_contours = [
                                c for c in contours
                                if cv2.contourArea(c) > min_area
                            ]

                            # 多个独立区域可能是点选验证码
                            if len(significant_contours) >= 4:
                                logger.debug(
                                    f"[CAPTCHA] 检测到 {len(significant_contours)} 个独立区域，"
                                    f"判断为点选验证码"
                                )
                                return CaptchaType.CLICK

                            # 检查是否有明显缺口（滑块特征）
                            # 垂直投影分析
                            projection = np.sum(edges, axis=0)
                            mean_proj = np.mean(projection)
                            std_proj = np.std(projection)

                            # 如果有突出的峰值，可能是滑块缺口
                            if std_proj > mean_proj * 0.5:
                                logger.debug("[CAPTCHA] 检测到缺口特征，判断为滑块验证码")
                                return CaptchaType.SLIDER

                    except ImportError:
                        pass  # OpenCV 不可用，跳过深度分析

                # 特征4: 检测是否接近正方形（可能是旋转验证码）
                if 0.9 < aspect_ratio < 1.1 and width > 100:
                    logger.debug(f"[CAPTCHA] 接近正方形，判断为旋转验证码")
                    return CaptchaType.ROTATE

            except ImportError:
                logger.warning("[CAPTCHA] Pillow 未安装，使用默认检测")

            # 默认返回文字验证码
            return CaptchaType.TEXT

        except Exception as e:
            logger.warning(f"[CAPTCHA] 类型检测失败: {e}，使用默认类型")
            return CaptchaType.TEXT

    def _record_result(self, result: CaptchaResult):
        """记录识别结果"""
        if result.success:
            self.stats["success"] += 1
        else:
            self.stats["failure"] += 1

        # 按类型统计
        type_key = result.captcha_type.value
        if type_key not in self.stats["by_type"]:
            self.stats["by_type"][type_key] = {"total": 0, "success": 0}
        self.stats["by_type"][type_key]["total"] += 1
        if result.success:
            self.stats["by_type"][type_key]["success"] += 1

        # 按方法统计
        method_key = result.method
        if method_key not in self.stats["by_method"]:
            self.stats["by_method"][method_key] = {"total": 0, "success": 0}
        self.stats["by_method"][method_key]["total"] += 1
        if result.success:
            self.stats["by_method"][method_key]["success"] += 1

    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = self.stats.copy()
        if stats["total"] > 0:
            stats["success_rate"] = stats["success"] / stats["total"]
        else:
            stats["success_rate"] = 0.0
        return stats


# ============================================================================
# 图片预处理工具
# ============================================================================

class ImagePreprocessor:
    """图片预处理工具

    提供多种预处理方法，用于提高验证码识别准确率
    """

    @staticmethod
    def preprocess(
        image_bytes: bytes,
        operations: List[str] = None
    ) -> bytes:
        """
        预处理验证码图片

        Args:
            image_bytes: 原始图片字节
            operations: 要执行的操作列表，可选值:
                - "grayscale": 灰度化
                - "binarize": 二值化
                - "denoise": 去噪
                - "contrast": 增强对比度
                - "sharpen": 锐化
                - "remove_border": 去除边框
                如果为 None，执行默认操作序列

        Returns:
            处理后的图片字节
        """
        if operations is None:
            operations = ["grayscale", "contrast", "binarize", "denoise"]

        try:
            from PIL import Image, ImageEnhance, ImageFilter
            import io

            # 加载图片
            img = Image.open(io.BytesIO(image_bytes))

            # 转换为 RGB (处理 RGBA/P 等模式)
            if img.mode not in ['RGB', 'L']:
                img = img.convert('RGB')

            # 按顺序执行操作
            for op in operations:
                if op == "grayscale":
                    img = ImagePreprocessor._to_grayscale(img)
                elif op == "binarize":
                    img = ImagePreprocessor._binarize(img)
                elif op == "denoise":
                    img = ImagePreprocessor._denoise(img)
                elif op == "contrast":
                    img = ImagePreprocessor._enhance_contrast(img)
                elif op == "sharpen":
                    img = ImagePreprocessor._sharpen(img)
                elif op == "remove_border":
                    img = ImagePreprocessor._remove_border(img)

            # 输出为 PNG 字节
            output = io.BytesIO()
            img.save(output, format='PNG')
            return output.getvalue()

        except ImportError:
            logger.warning("[CAPTCHA] Pillow 未安装，跳过预处理")
            return image_bytes
        except Exception as e:
            logger.error(f"[CAPTCHA] 预处理失败: {e}")
            return image_bytes

    @staticmethod
    def _to_grayscale(img):
        """灰度化"""
        return img.convert('L')

    @staticmethod
    def _binarize(img, threshold: int = 128):
        """
        二值化

        Args:
            img: PIL Image 对象
            threshold: 阈值 (0-255)
        """
        # 确保是灰度图
        if img.mode != 'L':
            img = img.convert('L')

        # 简单阈值二值化
        return img.point(lambda x: 255 if x > threshold else 0)

    @staticmethod
    def _adaptive_binarize(img):
        """自适应二值化 (使用 OpenCV)"""
        try:
            import cv2
            import numpy as np
            from PIL import Image
            import io

            # PIL -> OpenCV
            img_array = np.array(img)
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array

            # 自适应阈值
            binary = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11, 2
            )

            # OpenCV -> PIL
            return Image.fromarray(binary)

        except ImportError:
            return ImagePreprocessor._binarize(img)

    @staticmethod
    def _denoise(img):
        """去噪"""
        try:
            from PIL import ImageFilter

            # 中值滤波去噪
            if img.mode == 'L':
                return img.filter(ImageFilter.MedianFilter(size=3))
            else:
                return img.filter(ImageFilter.MedianFilter(size=3))

        except Exception:
            return img

    @staticmethod
    def _enhance_contrast(img, factor: float = 1.5):
        """
        增强对比度

        Args:
            img: PIL Image 对象
            factor: 对比度因子 (1.0 为原始, >1 增强, <1 降低)
        """
        try:
            from PIL import ImageEnhance

            enhancer = ImageEnhance.Contrast(img)
            return enhancer.enhance(factor)

        except Exception:
            return img

    @staticmethod
    def _sharpen(img):
        """锐化"""
        try:
            from PIL import ImageFilter

            return img.filter(ImageFilter.SHARPEN)

        except Exception:
            return img

    @staticmethod
    def _remove_border(img, border_width: int = 2):
        """
        去除边框

        Args:
            img: PIL Image 对象
            border_width: 边框宽度 (像素)
        """
        width, height = img.size

        if width <= border_width * 2 or height <= border_width * 2:
            return img

        return img.crop((
            border_width,
            border_width,
            width - border_width,
            height - border_width
        ))

    @staticmethod
    def preprocess_for_ocr(image_bytes: bytes) -> bytes:
        """
        针对 OCR 优化的预处理

        专门优化文字验证码识别效果
        """
        return ImagePreprocessor.preprocess(
            image_bytes,
            operations=[
                "grayscale",
                "contrast",
                "sharpen",
                "binarize",
                "denoise"
            ]
        )

    @staticmethod
    def preprocess_for_slider(image_bytes: bytes) -> bytes:
        """
        针对滑块验证码优化的预处理

        增强边缘特征
        """
        try:
            import cv2
            import numpy as np
            import io

            # 解码
            img_array = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if img is None:
                return image_bytes

            # 转灰度
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 高斯模糊
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)

            # 增强对比度 (CLAHE)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(blurred)

            # 编码输出
            _, encoded = cv2.imencode('.png', enhanced)
            return encoded.tobytes()

        except ImportError:
            logger.warning("[CAPTCHA] OpenCV 未安装，跳过滑块预处理")
            return image_bytes
        except Exception as e:
            logger.error(f"[CAPTCHA] 滑块预处理失败: {e}")
            return image_bytes

    @staticmethod
    def remove_watermark(image_bytes: bytes, color_threshold: int = 200) -> bytes:
        """
        去除浅色水印

        Args:
            image_bytes: 原始图片
            color_threshold: 颜色阈值，高于此值的像素变为白色
        """
        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_bytes))

            if img.mode != 'RGB':
                img = img.convert('RGB')

            # 遍历像素，去除浅色
            pixels = img.load()
            width, height = img.size

            for y in range(height):
                for x in range(width):
                    r, g, b = pixels[x, y]
                    # 如果像素接近白色，设为白色
                    if r > color_threshold and g > color_threshold and b > color_threshold:
                        pixels[x, y] = (255, 255, 255)

            output = io.BytesIO()
            img.save(output, format='PNG')
            return output.getvalue()

        except ImportError:
            return image_bytes
        except Exception as e:
            logger.error(f"[CAPTCHA] 去水印失败: {e}")
            return image_bytes


# ============================================================================
# 使用示例
# ============================================================================

def example_usage():
    """使用示例"""
    print("=" * 80)
    print("验证码识别模块 - 使用示例")
    print("=" * 80)

    # 1. 创建管理器
    manager = CaptchaManager()

    # 2. 注册识别器
    manager.register(CaptchaType.TEXT, DDDOCRRecognizer(), priority=0)
    manager.register(CaptchaType.SLIDER, SliderRecognizer(), priority=0)
    manager.register(CaptchaType.CLICK, ClickRecognizer(), priority=0)

    # 3. 识别图形验证码
    print("\n示例 1: 识别图形验证码")
    print("-" * 80)
    # result = manager.recognize("captcha.png", CaptchaType.TEXT)
    # print(result)

    # 4. 生成滑块轨迹
    print("\n示例 2: 生成滑块轨迹")
    print("-" * 80)
    distance = 120  # 滑动距离
    track = TrajectoryGenerator.generate_bezier_track(distance)
    print(f"轨迹点数: {len(track.points)}")
    print(f"总距离: {track.distance}px")
    print(f"总时长: {track.duration_ms}ms")
    print(f"算法: {track.algorithm}")
    print(f"前5个点: {track.points[:5]}")

    # 5. 物理模拟轨迹
    print("\n示例 3: 物理模拟轨迹")
    print("-" * 80)
    track2 = TrajectoryGenerator.generate_physics_track(distance)
    print(f"轨迹点数: {len(track2.points)}")
    print(f"总距离: {track2.distance}px")
    print(f"总时长: {track2.duration_ms}ms")
    print(f"算法: {track2.algorithm}")
    print(f"前5个点: {track2.points[:5]}")

    # 6. 统计信息
    print("\n示例 4: 统计信息")
    print("-" * 80)
    stats = manager.get_stats()
    print(f"总识别次数: {stats['total']}")
    print(f"成功次数: {stats['success']}")
    print(f"失败次数: {stats['failure']}")
    print(f"成功率: {stats['success_rate']:.2%}")


if __name__ == "__main__":
    example_usage()
