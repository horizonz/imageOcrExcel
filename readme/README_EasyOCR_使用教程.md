**简介**
- 本教程介绍基于 EasyOCR 的批量识别脚本 `mass_ocr_to_excel_easyocr.py` 的使用方法。
- 特点：严格按 ROI 边界识别、轻量预处理、可选调试切图、支持中文与中英文混排。

**环境要求**
- `Python 3.8+`
- 依赖：`easyocr`、`torch`、`pillow`、`numpy`、`pandas`、`tqdm`、`openpyxl`
- 安装示例：
  - `python3 -m pip install --upgrade pip`
  - `pip install easyocr pillow numpy pandas tqdm openpyxl` 
  - 若 `torch` 未装或失败（CPU）：`pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu`



**快速开始**
- 将待识别图片放入 `images/` 目录；配置好 `roi_config.json`。
- 运行：`python3 mass_ocr_to_excel_easyocr.py`
- 输出：生成 `ocr_result.csv` 与 `ocr_result.xlsx`（保存在脚本所在目录）。
- 首次运行会初始化 EasyOCR 模型，CPU 环境可能需要几十秒；脚本会打印初始化提示。

**ROI 配置**
- 文件：`roi_config.json`
- 每个 ROI 为归一化坐标，范围 `0~1`，相对于整张图片宽高：
  - `x`、`y`：左上角相对坐标；`w`、`h`：宽高相对比例。
- 示例：
  - ```
    {
      "rois": [
        {"name": "name",   "x": 0.32, "y": 0.43, "w": 0.18, "h": 0.06},
        {"name": "number", "x": 0.60, "y": 0.78, "w": 0.25, "h": 0.08}
      ]
    }
    ```
- 建议使用 `roi_configurator.py` 辅助定位 ROI，确保边界只覆盖目标文本行。

**脚本参数（文件顶部可配置）**
- `IMAGE_DIR`：图片目录（默认 `images`）。
- `ROI_CONFIG_PATH`：ROI 配置文件路径（默认 `roi_config.json`）。
- `OUTPUT_CSV` / `OUTPUT_XLSX`：输出文件名（默认分别为 `ocr_result.csv` / `ocr_result.xlsx`）。
- `STRICT_ROI`：严格使用 ROI，不扩边（默认 `True`）。
- `SMALL_ROI_MIN_HEIGHT` / `SMALL_ROI_MIN_WIDTH`：小 ROI 的判定阈值（默认 `40` / `80` 像素）。
- `SMALL_ROI_UPSCALE`：小 ROI 放大倍数（默认 `3`）。
- `SAVE_DEBUG_CROPS`：是否保存调试切图（默认 `False`，关闭）。
- `DEBUG_DIR`：调试切图目录（默认 `debug_crops_easy`）。
- `LANGS`：识别语言（默认 `["ch_sim", "en"]`）。仅中文场景可改为 `["ch_sim"]` 提升速度。
- `USE_GPU`：是否启用 GPU（默认 `False`，macOS CPU）。Apple Silicon 可测 MPS：`python -c "import torch; print(torch.backends.mps.is_available())"`。

**识别与后处理**
- 严格 ROI：只在配置的 `x/y/w/h` 范围内识别，不会扩边。
- 预处理：灰度 + 自动对比度；小 ROI（高度<`40` 或宽度<`80`）按 `3x` 放大后识别。
- 字段后处理：
  - `number`：保留字母数字，自动去除前缀 `No.`（不区分大小写）。
  - `name`：去除多余空白，保留中文字符。

**调试切图（默认关闭）**
- 开启方法：`SAVE_DEBUG_CROPS = True`。
- 保存位置：`debug_crops_easy/`，包含每个 ROI 的 `_raw.png`（严格裁剪）与 `_prep.png`（增强后输入）。
- 关闭后不会再创建或写入该目录；建议删除历史调试文件以节省空间。

**性能与优化**
- 吞吐参考（CPU，2 ROI/图）：约 `0.2–0.6 秒/张`。1k 张 ≈ `3–10 分钟`；1 万张 ≈ `50–170 分钟`。
- 影响因素：ROI 尺寸与数量、图片分辨率、语言数量（中文+英文略慢）、磁盘读写速度。
- 建议：
  - 仅中文：将 `LANGS` 改为 `["ch_sim"]`。
  - 关闭调试输出：`SAVE_DEBUG_CROPS=False`（默认已关闭）。
  - 优先 CSV：大批量时仅写 `csv`，如需 Excel 后处理再转换。
  - 分批运行：按 1k–2k 张分批，失败只需重跑该批。

**常见问题**
- 启动卡住：首次初始化 EasyOCR 模型较慢，耐心等待；脚本会打印初始化提示。
- 路径问题：脚本内部已统一使用相对脚本目录的绝对路径，在任意工作目录运行均可；确保 `images/` 与 `roi_config.json` 位于脚本所在目录。
- 没有输出或为空：检查 `roi_config.json` 的边界是否覆盖到目标文本；必要时开启调试切图定位问题。
- Excel 写入失败：安装 `openpyxl`；或先用 `csv` 输出。
- 调试目录还在生成：确认 `SAVE_DEBUG_CROPS=False` 且运行的是 `mass_ocr_to_excel_easyocr.py`。

**目录结构（示例）**
- `images/`：待识别图片
- `roi_config.json`：ROI 配置文件
- `mass_ocr_to_excel_easyocr.py`：EasyOCR 批量识别脚本
- `ocr_result.csv` / `ocr_result.xlsx`：识别结果
- `debug_crops_easy/`：调试切图（仅在开启时生成）

**使用建议**
- 在 `images/` 放少量样例图，先验证 ROI 与识别效果，再跑全量。
- 对于版式复杂、字段位置不固定的场景，考虑改用“检测+识别”的方案（如 MMOCR/云服务），速度会下降但鲁棒性更强。