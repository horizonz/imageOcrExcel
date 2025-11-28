import os
import sys

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

def run():
    try:
        from roi_configurator import main as roi_main
    except Exception as e:
        print(f"[ERROR] 加载 roi_configurator 失败: {e}")
        return 1
    try:
        roi_main()
    except Exception as e:
        print(f"[ERROR] 标注流程异常: {e}")
        return 1

    cfg_path = os.path.join(BASE_DIR, "roi_config.json")
    if not os.path.exists(cfg_path):
        print("[WARN] 未检测到 roi_config.json，已退出。")
        return 1

    try:
        from mass_ocr_to_excel_rapidocr import main as ocr_main
    except Exception as e:
        print(f"[ERROR] 加载批量识别脚本失败: {e}")
        return 1
    try:
        ocr_main()
    except Exception as e:
        print(f"[ERROR] 批量识别流程异常: {e}")
        return 1

    out_dir = os.path.join(BASE_DIR, "output")
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

