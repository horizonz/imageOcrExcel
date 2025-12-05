import os
import json
import cv2
import sys
import numpy as np
from typing import Optional, Tuple

# 可选：用于中文文字绘制与输入的支持
try:
    from PIL import Image as PILImage, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

try:
    import tkinter as tk
    from tkinter import simpledialog
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False


IMAGE_DIR = "images"
OUTPUT_JSON = "roi_config.json"

# 启用使用 PIL 在画面上绘制中文文字（OpenCV 默认字体不支持中文，显示为 ???）
USE_PIL_TEXT = True
# 是否启用中文输入（Tk 对话框）。在 Windows 上默认启用。
ENABLE_TK_INPUT = sys.platform.startswith("win")

# 常见系统中文字体路径（按平台尝试）
CJK_FONT_CANDIDATES = [
    # Windows
    r"C:\\Windows\\Fonts\\msyh.ttc",  # Microsoft YaHei
    r"C:\\Windows\\Fonts\\simhei.ttf",  # SimHei
    r"C:\\Windows\\Fonts\\simsun.ttc",  # SimSun
    # macOS
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    # Linux 常见路径（根据系统可能差异较大）
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]

FONT_CACHE = {}


def _load_cjk_font(size: int = 20) -> Optional[ImageFont.FreeTypeFont]:
    if not PIL_AVAILABLE:
        return None
    f = FONT_CACHE.get(size)
    if f is not None:
        return f
    for path in CJK_FONT_CANDIDATES:
        try:
            if os.path.exists(path):
                f = ImageFont.truetype(path, size)
                FONT_CACHE[size] = f
                return f
        except Exception:
            continue
    return None


def draw_text(frame, text: str, org: Tuple[int, int], color=(0, 255, 0), font_scale=0.6, thickness=2):
    """在图像上绘制文字，优先使用 PIL 支持中文；否则回退到 cv2.putText（仅 ASCII）。"""
    x, y = org
    if USE_PIL_TEXT and PIL_AVAILABLE:
        font = _load_cjk_font(size=int(22 * font_scale))
        if font is not None:
            # cv2 BGR -> PIL RGB
            try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = PILImage.fromarray(rgb)
                draw = ImageDraw.Draw(pil_img)
                # PIL 颜色为 RGB
                rgb_color = (color[2], color[1], color[0]) if len(color) == 3 else (0, 255, 0)
                draw.text((x, y), str(text), font=font, fill=rgb_color)
                # PIL RGB -> cv2 BGR
                frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                return frame
            except Exception:
                pass
    # 回退：OpenCV 英文字体（中文会显示为 ???）
    cv2.putText(frame, str(text), (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
    return frame

def draw_text_multiline(frame, text: str, org: Tuple[int, int], color=(0, 255, 0), font_scale=0.6, thickness=2, max_width: Optional[int] = None, line_spacing: int = 8):
    x, y = org
    s = str(text)
    if USE_PIL_TEXT and PIL_AVAILABLE:
        font = _load_cjk_font(size=int(22 * font_scale))
        if font is not None:
            try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = PILImage.fromarray(rgb)
                draw = ImageDraw.Draw(pil_img)
                rgb_color = (color[2], color[1], color[0]) if len(color) == 3 else (0, 255, 0)
                lines = [s]
                if max_width and max_width > 0:
                    unit = max(1, int(max_width / max(1, int(font.size * 0.9))))
                    lines = [s[i:i + unit] for i in range(0, len(s), unit)]
                for idx, ln in enumerate(lines):
                    draw.text((x, y + idx * (font.size + line_spacing)), ln, font=font, fill=rgb_color)
                frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                return frame
            except Exception:
                pass
    chunk = 40
    lines = [s[i:i + chunk] for i in range(0, len(s), chunk)]
    for idx, ln in enumerate(lines):
        cv2.putText(frame, ln, (x, y + int(idx * (22 * font_scale + line_spacing))), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
    return frame

def measure_text_height(text: str, font_scale: float, max_width: Optional[int] = None, line_spacing: int = 8) -> int:
    s = str(text)
    if USE_PIL_TEXT and PIL_AVAILABLE:
        font = _load_cjk_font(size=int(22 * font_scale))
        if font is not None:
            lines = [s]
            if max_width and max_width > 0:
                unit = max(1, int(max_width / max(1, int(font.size * 0.9))))
                lines = [s[i:i + unit] for i in range(0, len(s), unit)]
            return len(lines) * (font.size + line_spacing)
    chunk = 40
    lines = [s[i:i + chunk] for i in range(0, len(s), chunk)]
    return len(lines) * (int(22 * font_scale) + line_spacing)


def list_images(dir_path):
    exts = (".png", ".jpg", ".jpeg", ".bmp", ".tiff")
    return [
        os.path.join(dir_path, f)
        for f in os.listdir(dir_path)
        if f.lower().endswith(exts)
    ]


def draw_and_collect_rois(image_path, existing_cfg=None):
    img = cv2.imread(image_path)
    if img is None:
        try:
            data = np.fromfile(image_path, dtype=np.uint8)
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        except Exception:
            pass
    if img is None and PIL_AVAILABLE:
        try:
            pil_img = PILImage.open(image_path).convert("RGB")
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception:
            pass
    if img is None:
        raise RuntimeError(f"无法读取图片: {image_path}")

    clone = img.copy()
    # 新增：将 ROI 以字典保存，并在画框结束后即时命名
    rois = []  # new rois, each as {name, x, y, w, h} (normalized)
    drawing = False
    start_pt = (0, 0)
    current_rect = None  # (x1, y1, x2, y2)
    rect_finished = False

    HEADER_H_OFFSET = 260
    def mouse_cb(event, x, y, flags, param):
        nonlocal drawing, start_pt, current_rect, rect_finished, HEADER_H_OFFSET
        if y < HEADER_H_OFFSET:
            return
        adj_x = x
        adj_y = y - HEADER_H_OFFSET
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            ox = int(adj_x / scale)
            oy = int(adj_y / scale)
            start_pt = (ox, oy)
            current_rect = None
        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            ox = int(adj_x / scale)
            oy = int(adj_y / scale)
            current_rect = (start_pt[0], start_pt[1], ox, oy)
        elif event == cv2.EVENT_LBUTTONUP:
            drawing = False
            ox = int(adj_x / scale)
            oy = int(adj_y / scale)
            current_rect = (start_pt[0], start_pt[1], ox, oy)
            rect_finished = True

    window_name = "ROI标注: 左键拖拽画框 | u撤销 | c清空 | d丢弃已有 | s保存 | q退出"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(window_name, mouse_cb)

    h, w = img.shape[:2]
    max_w, max_h = 1280, 900
    scale = min(1.0, min(max_w / float(w), max_h / float(h)))
    dw, dh = int(w * scale), int(h * scale)
    base = cv2.resize(img, (dw, dh)) if scale != 1.0 else clone.copy()
    max_w, max_h = 1280, 900
    scale = min(1.0, min(max_w / float(w), max_h / float(h)))
    dw, dh = int(w * scale), int(h * scale)

    def prompt_text_in_window(prompt, default):
        """弹出命名输入。优先使用 Tk 对话框支持中文输入；回退到 ASCII 输入。"""
        if ENABLE_TK_INPUT and TK_AVAILABLE:
            try:
                root = tk.Tk()
                root.withdraw()
                # 让对话框出现在前台
                root.attributes('-topmost', True)
                value = simpledialog.askstring(title="输入列名", prompt=prompt, initialvalue=default)
                root.destroy()
                if value is None:
                    return default
                return value.strip() if value.strip() else default
            except Exception:
                pass
        # 回退：在 OpenCV 窗口中进行 ASCII 输入
        typed = ""
        while True:
            h1 = measure_text_height(prompt, 1.1, max_width=dw - 40, line_spacing=6)
            h2 = measure_text_height(f"输入：{typed}", 1.1, max_width=dw - 40, line_spacing=6)
            h3 = measure_text_height("回车确认 | ESC取消(默认) | 退格删除", 1.0, max_width=dw - 40, line_spacing=6)
            header_h_local = max(220, h1 + h2 + h3 + 40)
            nonlocal HEADER_H_OFFSET
            HEADER_H_OFFSET = header_h_local
            canvas = np.zeros((dh + header_h_local, dw, 3), dtype=np.uint8)
            canvas[header_h_local:header_h_local + dh, 0:dw] = base
            existing_count = 0
            if existing_cfg and existing_cfg.get("rois"):
                existing_count = len(existing_cfg["rois"])
                for r in existing_cfg["rois"]:
                    ex = int(r["x"] * w)
                    ey = int(r["y"] * h)
                    ew = int(r["w"] * w)
                    eh = int(r["h"] * h)
                    sx, sy, sw, sh = int(ex * scale), int(ey * scale), int(ew * scale), int(eh * scale)
                    sy += header_h_local
                    cv2.rectangle(canvas, (sx, sy), (sx + sw, sy + sh), (0, 255, 255), 2)
                    canvas = draw_text(canvas, r.get("name", "field"), (sx + 4, sy + 18), (0, 255, 255), 0.9, 2)
            for r in rois:
                ex = int(r["x"] * w)
                ey = int(r["y"] * h)
                ew = int(r["w"] * w)
                eh = int(r["h"] * h)
                sx, sy, sw, sh = int(ex * scale), int(ey * scale), int(ew * scale), int(eh * scale)
                sy += header_h_local
                cv2.rectangle(canvas, (sx, sy), (sx + sw, sy + sh), (0, 255, 0), 2)
                canvas = draw_text(canvas, r.get("name", "field"), (sx + 4, sy + 18), (0, 255, 0), 0.9, 2)
            y0 = 30
            canvas = draw_text_multiline(canvas, prompt, (20, y0), (255, 255, 255), 1.1, 2, max_width=dw - 40, line_spacing=6)
            y0 += h1 + 10
            canvas = draw_text_multiline(canvas, f"输入：{typed}", (20, y0), (0, 255, 0), 1.1, 2, max_width=dw - 40, line_spacing=6)
            y0 += h2 + 10
            canvas = draw_text_multiline(canvas, "回车确认 | ESC取消(默认) | 退格删除", (20, y0), (255, 255, 255), 1.0, 1, max_width=dw - 40, line_spacing=6)
            cv2.imshow(window_name, canvas)
            k = cv2.waitKey(0) & 0xFF
            try:
                vis = cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE)
                if vis < 1:
                    return default
            except Exception:
                pass
            if k in (13, 10):
                return typed.strip() if typed.strip() else default
            elif k in (27,):
                return default
            elif k in (8, 127):
                typed = typed[:-1]
            elif 32 <= k <= 126:
                typed += chr(k)

    try:
        while True:
            existing_count = 0
            if existing_cfg and existing_cfg.get("rois"):
                existing_count = len(existing_cfg["rois"])
            s1 = "左键拖拽画框; u撤销; c清空; d丢弃黄色; s保存; q退出; ESC退出"
            s2 = f"已存在字段: {existing_count}  | 新增框: {len(rois)}"
            s3 = "提示: 每个框画完即命名；按 s 一次性保存"
            s4 = "提示: 仅按字母键执行操作（s/u/c/d/q），避免 Ctrl 组合键"
            h1 = measure_text_height(s1, 1.0, max_width=dw - 40, line_spacing=6)
            h2 = measure_text_height(s2, 0.9, max_width=dw - 40, line_spacing=6)
            h3 = measure_text_height(s3, 0.85, max_width=dw - 40, line_spacing=6)
            h4 = measure_text_height(s4, 0.9, max_width=dw - 40, line_spacing=6)
            header_h = max(220, h1 + h2 + h3 + h4 + 40)
            HEADER_H_OFFSET = header_h
            display = np.zeros((dh + header_h, dw, 3), dtype=np.uint8)
            display[header_h:header_h + dh, 0:dw] = base

            # draw existing config rois (in yellow)
            if existing_cfg and existing_cfg.get("rois"):
                for r in existing_cfg["rois"]:
                    ex = int(r["x"] * w)
                    ey = int(r["y"] * h)
                    ew = int(r["w"] * w)
                    eh = int(r["h"] * h)
                    sx, sy, sw, sh = int(ex * scale), int(ey * scale), int(ew * scale), int(eh * scale)
                    sy += header_h
                    cv2.rectangle(display, (sx, sy), (sx + sw, sy + sh), (0, 255, 255), 2)
                    display = draw_text(display, r.get("name", "field"), (sx + 4, sy + 18), (0, 255, 255), 0.6, 2)

            # draw new rois (in green)
            for r in rois:
                ex = int(r["x"] * w)
                ey = int(r["y"] * h)
                ew = int(r["w"] * w)
                eh = int(r["h"] * h)
                sx, sy, sw, sh = int(ex * scale), int(ey * scale), int(ew * scale), int(eh * scale)
                sy += header_h
                cv2.rectangle(display, (sx, sy), (sx + sw, sy + sh), (0, 255, 0), 2)
                display = draw_text(display, r.get("name", "field"), (sx + 4, sy + 18), (0, 255, 0), 0.6, 2)

            # draw current rect (in blue)
            if current_rect is not None and drawing:
                (x1, y1, x2, y2) = current_rect
                x = min(x1, x2)
                y = min(y1, y2)
                rw = abs(x2 - x1)
                rh = abs(y2 - y1)
                sx, sy, srw, srh = int(x * scale), int(y * scale), int(rw * scale), int(rh * scale)
                sy += header_h
                cv2.rectangle(display, (sx, sy), (sx + srw, sy + srh), (255, 0, 0), 1)

            y0 = 30
            display = draw_text_multiline(display, s1, (20, y0), (255, 255, 255), 1.0, 2, max_width=dw - 40, line_spacing=6)
            y0 += h1 + 8
            display = draw_text_multiline(display, s2, (20, y0), (255, 255, 255), 0.9, 2, max_width=dw - 40, line_spacing=6)
            y0 += h2 + 8
            display = draw_text_multiline(display, s3, (20, y0), (255, 255, 255), 0.85, 2, max_width=dw - 40, line_spacing=6)
            y0 += h3 + 8
            display = draw_text_multiline(display, s4, (20, y0), (255, 255, 255), 0.9, 2, max_width=dw - 40, line_spacing=6)

            cv2.imshow(window_name, display)
            key = cv2.waitKey(20) & 0xFF

            # allow closing if window was closed by user
            try:
                vis = cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE)
                if vis < 1:
                    return None
            except Exception:
                pass

            # 画框结束：弹窗命名并加入 rois
            if rect_finished and current_rect is not None:
                (x1, y1, x2, y2) = current_rect
                x = min(x1, x2)
                y = min(y1, y2)
                ww = abs(x2 - x1)
                hh = abs(y2 - y1)
                default_name = f"field_{len(rois) + 1}"
                name = prompt_text_in_window(f"为新区域输入列名：", default_name)
                rois.append({
                    "name": name,
                    "x": x / w,
                    "y": y / h,
                    "w": ww / w,
                    "h": hh / h,
                })
                # 重置状态，避免重复弹窗
                current_rect = None
                rect_finished = False

            if key == 27:  # ESC
                return None
            elif (key == ord('u')) and rois:  # 仅支持字母键操作，避免 Ctrl 组合键
                rois.pop()
            elif key == ord('c'):  # 仅支持字母键操作
                rois.clear()
            elif key == ord('d'):  # 仅支持字母键操作
                # 丢弃已存在的黄色字段，仅保留本次新增
                existing_cfg = None
            elif key == ord('q'):  # 仅支持字母键操作
                return None
            elif key == ord('s'):  # 仅支持字母键操作
                # 保存：合并并去重（按名称去重，后者覆盖前者）
                def _merge_dedup(existing_list, new_list):
                    by_name = {}
                    for r in (existing_list or []):
                        n = str(r.get("name", "field"))
                        by_name[n] = r
                    for r in (new_list or []):
                        n = str(r.get("name", "field"))
                        by_name[n] = r  # 新的覆盖旧的同名字段
                    return list(by_name.values())

                if existing_cfg and existing_cfg.get("rois"):
                    merged_rois = _merge_dedup(existing_cfg.get("rois", []), rois)
                    return {
                        "template_image": existing_cfg.get("template_image", os.path.basename(image_path)),
                        "template_size": {"width": w, "height": h},
                        "rois": merged_rois,
                    }
                else:
                    return {
                        "template_image": os.path.basename(image_path),
                        "template_size": {"width": w, "height": h},
                        "rois": rois,
                    }
    finally:
        try:
            cv2.destroyAllWindows()
            cv2.waitKey(1)
        except Exception:
            pass


def load_existing_config(path):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if isinstance(cfg, dict) and cfg.get("rois"):
                    return cfg
    except Exception:
        pass
    return None


def main():
    images = list_images(IMAGE_DIR)
    if not images:
        print(f"未在 {IMAGE_DIR} 找到图片")
        return

    existing_cfg = load_existing_config(OUTPUT_JSON)
    if existing_cfg:
        print(f"检测到已有配置文件：{OUTPUT_JSON}，当前字段数：{len(existing_cfg.get('rois', []))}。保存将追加新字段。")
    print(f"共发现 {len(images)} 张图片。将以首张图片作为模板进行标注。")
    config = draw_and_collect_rois(images[0], existing_cfg=existing_cfg)
    if config is None:
        print("未保存配置，已退出。")
        return

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"✅ ROI配置已保存到 {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
