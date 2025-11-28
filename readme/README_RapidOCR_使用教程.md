简介
- 本教程介绍基于 RapidOCR-ONNXRuntime 的批量识别脚本 `mass_ocr_to_excel_rapidocr.py` 的使用方法。
- 特点：启动快（1–5 秒）、CPU 识别快、严格按 ROI 识别、轻量预处理、可选调试切图、输出 CSV/XLSX。

环境要求
- Python 3.8+
- 依赖：`rapidocr-onnxruntime`、`pillow`、`numpy`、`pandas`、`tqdm`、`openpyxl`
- 安装示例：
  - `python3 -m pip install --upgrade pip`
  - `pip install rapidocr-onnxruntime pillow numpy pandas tqdm openpyxl`
  - 验证安装：`python -c "from rapidocr_onnxruntime import RapidOCR; print('ok')"`

快速开始
- 将待识别图片放入 `images/` 目录；配置好 `roi_config.json`。
- 运行：`python3 mass_ocr_to_excel_rapidocr.py`
- 输出：生成 `ocr_result.csv` 与 `ocr_result.xlsx`（保存在脚本所在目录）。
- 启动提示：脚本会打印“初始化 RapidOCR”与完成信息，随后显示图片总数和进度条。

ROI 配置
- 文件：`roi_config.json`
- 每个 ROI 为归一化坐标，范围 `0~1`，相对于整张图片宽高：
  - `x`、`y`：左上角相对坐标；`w`、`h`：宽高相对比例。
- 示例：
  - {
    "rois": [
      {"name": "name",   "x": 0.32, "y": 0.43, "w": 0.18, "h": 0.06},
      {"name": "number", "x": 0.60, "y": 0.78, "w": 0.25, "h": 0.08}
    ]
    }
- 建议使用 `roi_configurator.py` 辅助定位 ROI，确保边界仅覆盖目标文本行，不包含多余背景或多行内容。

脚本参数（文件顶部）
- `IMAGE_DIR`：图片目录（默认 `images`）。
- `ROI_CONFIG_PATH`：ROI 配置文件（默认 `roi_config.json`）。
- `OUTPUT_CSV` / `OUTPUT_XLSX`：结果输出文件名。
- `STRICT_ROI`：严格使用 ROI，不扩边（建议保持 True）。
- `SMALL_ROI_MIN_HEIGHT` / `SMALL_ROI_MIN_WIDTH`：判定“小 ROI”的阈值（默认 40/80 像素）。
- `SMALL_ROI_UPSCALE`：小 ROI 放大倍数（默认 3）。
- `SAVE_DEBUG_CROPS`：是否保存调试切图（默认 False）。
- `DEBUG_DIR`：调试切图输出目录（默认 `debug_crops_rapid/`）。
- `USE_DET`：是否启用检测模型（严格 ROI 场景建议 False，更快）。

识别与后处理策略
- 严格 ROI：识别仅在 `roi_config.json` 指定的矩形内进行，不做扩边。
- 小 ROI 放大：当 ROI 高度<`SMALL_ROI_MIN_HEIGHT` 或宽度<`SMALL_ROI_MIN_WIDTH` 时，按 `SMALL_ROI_UPSCALE` 倍放大后再识别，提升细字清晰度。
- 轻度预处理：灰度 + 自动对比度，避免过度锐化造成笔画断裂。
- 识别路径：
  - 首选“纯识别”（`USE_DET=False`）直接对 ROI 子图识别，速度更快。
  - 若结果为空，脚本会回退启用检测进行一次识别，增强容错能力。
- 文本清洗：
  - `number`：去除 `No.` 前缀，保留大写字母与数字（适配如 `RRFP04012208010111` 格式）。
  - `name`：去除空白，仅保留中文字符。
- 输出类型：
  - 为避免 Excel 将长数字显示为科学计数法，脚本会在写出前将 ROI 字段显式转换为字符串。

调试与排错
- 打开切图：将 `SAVE_DEBUG_CROPS=True`，脚本会在 `debug_crops_rapid/` 保存 `raw` 和 `prep` 切图，便于检查 ROI 是否覆盖正确及预处理效果。
- 结果为空：通常是 ROI 边界未覆盖目标文字、背景干扰、或文本过细。可适当收紧 ROI、提高 `SMALL_ROI_UPSCALE`，或手动扩大 ROI。
- 路径问题：脚本使用相对脚本目录的绝对路径，避免工作目录不同导致找不到文件。
- 异常信息：若某图识别异常，输出会在对应列显示 `[ERROR] ...` 文本，便于定位问题。

性能优化建议
- 启动时间：RapidOCR（ONNXRuntime）通常 1–5 秒；明显快于 EasyOCR 的 20–60 秒。
- 识别速度：严格 ROI 的小图识别下，常见 0.06–0.24 秒/张（2 ROI/图）。
- 批量运行：
  - 一次处理大量图片，避免重复初始化。
  - 关闭调试切图，仅输出 CSV/XLSX。
  - 若需断点续跑，我可以为你添加“分批保存与自动合并”的机制（同 Tesseract 版）。
- ROI 调整：更紧的 ROI、适当放大可提升速度与准确率，同时减少背景干扰。

常见问题与解法
- Excel 科学计数法：`number` 这类长数字被 Excel 自动格式化为 `E+15` 显示。脚本已将列转换为字符串，正常显示。如果你希望在 Excel 中保留数字格式，请在 Excel 中将该列设置为“文本”或自定义格式。
- 识别文本被写成置信度：RapidOCR 的返回结构可能是 `[text, score]`、`[bbox, text, score]` 或字典。脚本已修复解析，始终写入文本，不再写入 0.xxx 的置信度数字。
- 警告输出：脚本已过滤不关键的 `pin_memory` 类性能警告，避免控制台噪声；不影响识别结果。
- ROI 不准导致误识别：开启切图检查；必要时收紧或略微移动 ROI，确保只覆盖目标行。

附：实践建议
- 先小批量（10–50 张）试跑，核对每列是否符合预期，再跑全量。
- 统一文件命名规则，便于定位问题图片（例如前缀包含用户名或编号）。
- 当模板变化时为不同模板维护独立的 `roi_config.json`，并通过脚本参数切换。

反馈与扩展
- 如果你需要：
  - 增加命令行开关（如 `--save-csv-only`、`--upscale 4`、`--enable-det-fallback`）。
  - 常驻“服务模式”（脚本常驻内存，持续接收图片路径队列）。
  - README 中加入图示/示例表格。
- 告诉我你的偏好，我会直接为你加上并提供使用说明。

打包为 Windows 可执行文件（.exe）
- 构建环境：请在 Windows 电脑上构建（PyInstaller 需在目标平台打包）。
- 安装依赖：
  - `python -m pip install --upgrade pip`
  - `pip install pyinstaller rapidocr-onnxruntime pillow numpy pandas tqdm openpyxl`
- 打包命令（示例）：
  - `pyinstaller --onefile --name MassOCRRapid --collect-all rapidocr_onnxruntime --add-data "roi_config.json;." mass_ocr_to_excel_rapidocr.py`
  - 说明：
    - `--onefile` 打成单文件 exe；
    - `--collect-all rapidocr_onnxruntime` 收集 RapidOCR 模型与资源；
    - `--add-data "roi_config.json;."` 将 ROI 配置打到 exe 同目录（Windows 使用分号分隔 `源;目标`）。
- 运行与目录结构：
  - 将 `images/` 文件夹与打包好的 `MassOCRRapid.exe` 放在同一目录；
  - 若使用多个模板，可把 `config 不同证书模版目录（删除中文使用）/` 放在同目录。
- 注意事项：
  - 打包后脚本已自动识别可执行文件目录作为基准路径（已适配 `sys.frozen`）；
  - 如需包含更多资源文件，重复使用 `--add-data`；
  - EasyOCR 版本可打包，但体积更大（需包含 CPU 版 Torch），推荐优先使用 RapidOCR 版本。

（可选）制作安装包
- 你可以使用 Inno Setup 或 NSIS 把 `MassOCRRapid.exe` 与资源文件封装为安装程序：
  - 将 `images/`、`roi_config.json`、相关 `config/` 模板作为安装目录中的可选内容；
  - 安装后用户可直接在安装目录放入新的图片运行。