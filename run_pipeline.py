import os
import sys
import ctypes

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

def run():
    out_dir = os.path.join(BASE_DIR, "output")
    try:
        os.makedirs(out_dir, exist_ok=True)
    except Exception:
        pass

    log_path = os.path.join(out_dir, "run_log.txt")
    def log(msg):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(str(msg) + "\n")
        except Exception:
            pass

    def alert(msg, title="提示"):
        try:
            if sys.platform.startswith("win"):
                ctypes.windll.user32.MessageBoxW(0, str(msg), str(title), 0)
                return
        except Exception:
            pass
        if sys.platform == "darwin":
            try:
                m = str(msg).replace('"', '\\"')
                t = str(title).replace('"', '\\"')
                script = "osascript -e 'display dialog \"" + m + "\" with title \"" + t + "\" buttons {\"OK\"}'"
                os.system(script)
                return
            except Exception:
                pass
        print(msg)

    images_dir = os.path.join(BASE_DIR, "images")
    log(f"BASE_DIR={BASE_DIR}")
    log(f"Checking images dir: {images_dir}")
    if not os.path.isdir(images_dir):
        alert(f"未找到 images 目录：{images_dir}\n请在与程序同级创建 images 并放入图片后重试。")
        log("images dir missing")
        return 1
    has_image = any(str(f).lower().endswith((".png", ".jpg", ".jpeg")) for f in os.listdir(images_dir))
    if not has_image:
        alert("images 目录为空或无图片文件。请放入待识别图片后重试。")
        log("no images found")
        return 1
    try:
        from roi_configurator import main as roi_main
    except Exception as e:
        log(f"load roi_configurator failed: {e}")
        print(f"[ERROR] 加载 roi_configurator 失败: {e}")
        return 1
    try:
        log("starting roi_configurator")
        roi_main()
    except Exception as e:
        alert(f"标注流程异常：{e}")
        log(f"roi_configurator error: {e}")
        return 1

    cfg_path = os.path.join(BASE_DIR, "roi_config.json")
    if not os.path.exists(cfg_path):
        alert("未检测到 roi_config.json。请在标注界面按 S 或 Ctrl+S 保存后再继续。")
        log("roi_config.json missing after roi")
        return 1
    else:
        log("config saved, starting OCR")

    try:
        from mass_ocr_to_excel_rapidocr import main as ocr_main
    except Exception as e:
        log(f"load rapidocr script failed: {e}")
        alert(f"加载批量识别脚本失败：{e}\n请确认已安装依赖 rapidocr-onnxruntime、pillow、pandas、tqdm、numpy、opencv-python、openpyxl。")
        return 1
    try:
        log("starting mass_ocr_to_excel_rapidocr")
        ocr_main()
    except Exception as e:
        alert(f"批量识别流程异常：{e}")
        log(f"ocr error: {e}")
        return 1
    alert("处理完成，结果已输出到 output 目录。")
    log("done, opening output dir")
    try:
        if sys.platform.startswith("win"):
            os.startfile(out_dir)
        elif sys.platform == "darwin":
            os.system(f"open '{out_dir}'")
        else:
            os.system(f"xdg-open '{out_dir}'")
    except Exception:
        pass
    return 0

if __name__ == "__main__":
    code = run()
    sys.exit(code)
