import os
import sys
import json
import re
import warnings
from typing import List
import numpy as np
from PIL import Image, ImageOps
import pandas as pd
from tqdm import tqdm

# 过滤不关键的性能类警告
warnings.filterwarnings("ignore", message=r".*'pin_memory'.*")

try:
    from rapidocr_onnxruntime import RapidOCR
except Exception as e:
    raise RuntimeError("未安装 rapidocr-onnxruntime，请先安装：pip install rapidocr-onnxruntime")

# ========== 配置区域 ==========
IMAGE_DIR = "images"                 # 图片文件夹
ROI_CONFIG_PATH = "roi_config.json"   # ROI 配置文件
OUTPUT_DIR = "output"
OUTPUT_CSV = "ocr_result.csv"
OUTPUT_XLSX = "ocr_result.xlsx"
STRICT_ROI = True                     # 严格使用 ROI，不扩边
SMALL_ROI_MIN_HEIGHT = 40             # ROI高度小于该值时先放大
SMALL_ROI_MIN_WIDTH = 80              # ROI宽度小于该值时先放大
SMALL_ROI_UPSCALE = 3                 # 小ROI放大倍数
SAVE_DEBUG_CROPS = False              # 是否保存调试切图（默认关闭）
DEBUG_DIR = "debug_crops_rapid"        # 调试切图目录
USE_DET = False                       # 是否启用检测模型（严格ROI下建议关闭以提速）
# ============================

# 兼容打包后运行（PyInstaller 一文件模式）：优先使用可执行文件所在目录
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ocr_engine = None


def load_roi_config(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到 ROI 配置文件: {path}")
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    rois = cfg.get("rois", [])
    if not rois:
        raise ValueError("ROI 配置为空或格式错误")
    ordered_names = []
    seen = set()
    filtered = []
    for r in rois:
        name = r.get("name")
        if not name:
            continue
        if name not in seen:
            ordered_names.append(name)
            seen.add(name)
        filtered.append({
            "name": name,
            "x": float(r.get("x", 0)),
            "y": float(r.get("y", 0)),
            "w": float(r.get("w", 0)),
            "h": float(r.get("h", 0)),
        })
    return filtered, ordered_names


def crop_by_roi(pil_img: Image.Image, roi: dict):
    """严格按归一化 ROI 裁剪，不扩边"""
    w, h = pil_img.size
    nx = max(0.0, min(1.0, float(roi.get("x", 0))))
    ny = max(0.0, min(1.0, float(roi.get("y", 0))))
    nw = max(0.0, min(1.0, float(roi.get("w", 0))))
    nh = max(0.0, min(1.0, float(roi.get("h", 0))))

    x = int(nx * w)
    y = int(ny * h)
    rw = int(nw * w)
    rh = int(nh * h)

    x = max(0, min(x, w - 1))
    y = max(0, min(y, h - 1))
    rw = max(1, min(rw, w - x))
    rh = max(1, min(rh, h - y))
    return pil_img.crop((x, y, x + rw, y + rh))


def enhance_for_ocr(img: Image.Image) -> Image.Image:
    """轻度增强：灰度+自动对比度"""
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g)
    return g.convert("RGB")


def _to_numpy_rgb(img: Image.Image) -> np.ndarray:
    if img.mode != "RGB":
        img = img.convert("RGB")
    return np.array(img)


def init_ocr(use_det: bool = USE_DET):
    global ocr_engine
    print("🚀 正在初始化 RapidOCR（CPU，ONNXRuntime）…", flush=True)
    try:
        ocr_engine = RapidOCR(use_det=use_det)
    except TypeError:
        # 某些版本不支持 use_det 参数，回退为默认
        ocr_engine = RapidOCR()
        if use_det is False:
            print("ℹ️ 当前 RapidOCR 版本不支持禁用检测参数，已回退到默认初始化。", flush=True)
    print("✅ RapidOCR 初始化完成", flush=True)


def read_text(img: Image.Image) -> str:
    np_img = _to_numpy_rgb(img)
    try:
        result, _ = ocr_engine(np_img)
        # 兼容多种返回结构：
        # - [bbox, text, score]
        # - [text, score]
        # - {"text": str, "score": float, ...}
        if isinstance(result, list) and result:
            texts = []
            for item in result:
                try:
                    if isinstance(item, dict):
                        txt = item.get("text", "")
                        if txt:
                            texts.append(str(txt))
                            continue
                    if isinstance(item, (list, tuple)):
                        # 优先使用字符串元素作为文本
                        if len(item) >= 2:
                            if isinstance(item[1], str):
                                texts.append(item[1])
                                continue
                            if isinstance(item[0], str):
                                texts.append(item[0])
                                continue
                        # 回退：扫描所有字符串字段
                        for elem in item:
                            if isinstance(elem, str):
                                texts.append(elem)
                                break
                except Exception:
                    pass
            return "".join(t.strip() for t in texts)
        # 回退：若空且当前禁用检测，可临时启用检测再识别
        try:
            det_ocr = RapidOCR(use_det=True)
            result2, _ = det_ocr(np_img)
            texts2 = []
            for it in (result2 or []):
                try:
                    if isinstance(it, dict):
                        txt = it.get("text", "")
                        if txt:
                            texts2.append(str(txt))
                            continue
                    if isinstance(it, (list, tuple)):
                        if len(it) >= 2:
                            if isinstance(it[1], str):
                                texts2.append(it[1])
                                continue
                            if isinstance(it[0], str):
                                texts2.append(it[0])
                                continue
                        for elem in it:
                            if isinstance(elem, str):
                                texts2.append(elem)
                                break
                except Exception:
                    pass
            return "".join(t.strip() for t in texts2)
        except Exception:
            return ""
    except Exception as e:
        return f"[ERROR] {e}"


def clean_number(text: str) -> str:
    if not text:
        return ""
    t = text.upper().strip()
    t = re.sub(r"^NO\.?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"[^A-Z0-9]", "", t)
    return t


def clean_name(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"[\s\r\n]+", "", text.strip())


def ocr_image(image_path: str, rois: List[dict], roi_names: List[str]) -> dict:
    fname = os.path.basename(image_path)
    row = {"filename": fname}
    try:
        pil_img = Image.open(image_path)
        if SAVE_DEBUG_CROPS:
            os.makedirs(os.path.join(BASE_DIR, DEBUG_DIR), exist_ok=True)
        for roi in rois:
            name = roi["name"].lower()
            crop = crop_by_roi(pil_img, roi)
            cw, ch = crop.size
            if ch < SMALL_ROI_MIN_HEIGHT or cw < SMALL_ROI_MIN_WIDTH:
                crop = crop.resize((cw * SMALL_ROI_UPSCALE, ch * SMALL_ROI_UPSCALE), Image.LANCZOS)
            if SAVE_DEBUG_CROPS:
                try:
                    crop.save(os.path.join(BASE_DIR, DEBUG_DIR, f"{os.path.splitext(fname)[0]}_{roi['name']}_raw.png"))
                except Exception:
                    pass
            prep = enhance_for_ocr(crop)
            if SAVE_DEBUG_CROPS:
                try:
                    prep.save(os.path.join(BASE_DIR, DEBUG_DIR, f"{os.path.splitext(fname)[0]}_{roi['name']}_prep.png"))
                except Exception:
                    pass
            text = read_text(prep)
            if any(k in name for k in ["number", "num", "编号", "号码", "id", "证号", "编码", "工号"]):
                text = clean_number(text)
            elif any(k in name for k in ["name", "姓名", "cname", "名称", "名字"]):
                text = clean_name(text)
            row[roi["name"]] = text
        for nm in roi_names:
            if nm not in row:
                row[nm] = ""
        return row
    except Exception as e:
        for nm in roi_names:
            row[nm] = f"[ERROR] {e}"
        return row


def main():
    roi_path = ROI_CONFIG_PATH if os.path.isabs(ROI_CONFIG_PATH) else os.path.join(BASE_DIR, ROI_CONFIG_PATH)
    images_dir = IMAGE_DIR if os.path.isabs(IMAGE_DIR) else os.path.join(BASE_DIR, IMAGE_DIR)
    out_dir = OUTPUT_DIR if os.path.isabs(OUTPUT_DIR) else os.path.join(BASE_DIR, OUTPUT_DIR)
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, OUTPUT_CSV) if not os.path.isabs(OUTPUT_CSV) else OUTPUT_CSV
    out_xlsx = os.path.join(out_dir, OUTPUT_XLSX) if not os.path.isabs(OUTPUT_XLSX) else OUTPUT_XLSX

    init_ocr(USE_DET)

    rois, roi_names = load_roi_config(roi_path)
    columns = ["filename"] + roi_names
    if not os.path.isdir(images_dir):
        raise FileNotFoundError(f"图片目录不存在：{images_dir}")
    all_images = [
        os.path.join(images_dir, f)
        for f in os.listdir(images_dir)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]
    print(f"📸 Found {len(all_images)} images. ROIs: {', '.join(roi_names)}", flush=True)
    results = []
    for img in tqdm(all_images, total=len(all_images), desc="Processing"):
        results.append(ocr_image(img, rois, roi_names))
    df = pd.DataFrame(results, columns=columns)
    # 显式将 ROI 字段转为字符串，避免 Excel 将长数字转换为科学计数法
    for col in roi_names:
        try:
            df[col] = df[col].astype(str)
        except Exception:
            pass
    df.to_csv(out_csv, index=False)
    df.to_excel(out_xlsx, index=False)
    print(f"\n🎉 All done! Results saved to {out_xlsx}", flush=True)


if __name__ == "__main__":
    main()
