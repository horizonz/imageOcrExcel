# 图像 ROI 批量识别与导出使用教程

本项目支持：
- 对样例图片标注多个 ROI（列字段），并保存为配置。
- 批量按 ROI 区域识别（中英混合文本），导出到 CSV/Excel。
- 额外生成 `username` 列：从图片文件名中提取中文姓名作为稳定参考。
- mass_ocr_to_excel 识别速度极快，但英和数字识别率高，中文较差
- mass_ocr_to_excel_easyocr 模型启动较慢，识别也较慢，但中英识别率都挺高
## 环境与依赖
- Python 3.8+
- 依赖安装：
  - `pip install pillow pandas pytesseract tqdm opencv-python`
- Tesseract OCR：
  - macOS：`brew install tesseract`
  - 确认中文语言包已安装：`tesseract --list-langs` 中应包含 `chi_sim`

## 目录结构
- `images/`：待识别图片放置目录
- `roi_configurator.py`：ROI 标注工具
- `roi_config.json`：当前生效的 ROI 配置文件（可由标注工具生成）
- `mass_ocr_to_excel.py`：批量识别并导出脚本
- `config目录/`：可选的多份 ROI 配置案例（不同模板）

## 快速开始
1) 将图片放到 `images/` 目录。
2) 运行 ROI 标注工具生成配置：
   ```bash
   python3 roi_configurator.py
   ```
   - 用鼠标左键拖拽画框，松开后输入列名（例如：`name`、`number`）。
   - 完成后按 `s` 或 `Ctrl+S` 保存到 `roi_config.json`。

3) 批量识别并导出：
   ```bash
   python3 mass_ocr_to_excel.py
   ```
   - 输出：`ocr_temp_batch_*.csv`（中间结果）、`ocr_result.csv`、`ocr_result.xlsx`。
   （中文识别较差，采用读取文件名称中xxx-xxxx-xxxx中间的用户名为username字段）

## ROI 配置说明（roi_config.json）
示例结构：
```json
{
  "template_image": "AAA_常佳俊_22233.jpg",
  "template_size": {"width": 1642, "height": 1270},
  "rois": [
    {"name": "name", "x": 0.36, "y": 0.446, "w": 0.262, "h": 0.085},
    {"name": "number", "x": 0.256, "y": 0.8, "w": 0.137, "h": 0.031}
  ]
}
```
- `x/y/w/h` 为归一化坐标（0~1），相对于模板图片尺寸。
- `name` 即导出的列名。

## 导出列与识别策略
- 导出列：`filename`、`username` + 所有 ROI 列（例如 `name`、`number`）。
- `username`：从文件名中提取中文姓名（优先按 `-` 分隔取中间段；无 `-` 时按 `_` 分隔；仍无中文则回退匹配首个中文片段）。
- 识别流程（统一通用）：
  - 裁剪 ROI → 灰度 → 自适应对比度 → 使用 `chi_sim+eng` 混合语言识别。
  - 不再对 `name/number` 做字符白名单或中文/英文限制，保留识别到的原始字符（去除首尾空白）。
- 数字与字母均可识别；如需严格格式（例如固定前缀、长度校验），可按需扩展。

## 多模板图片的使用建议
- 如果图片版式不同（如 `AAA_...` 与 `PAD_...`），ROI 位置会不同，建议：
  - 为每种版式分别标注并生成独立配置（位于 `config目录/`）。
  - 批量识别前，将对应配置复制或重命名为当前生效的 `roi_config.json`。
  - 或在脚本中按文件名前缀自动选择配置（可按需扩展）。

## 常见问题与排查
- 中文识别不准确：
  - 首先确认 ROI 确实裁剪到文字区域；必要时缩小框并避开底纹/线条。
  - 提升图像质量：尽量使用清晰、无强压缩的图片；避免阴影和反光。
  - 对中文姓名，单行文本更稳定；可将 ROI 框定为更紧凑的单行范围。
- 数字/英文字段误识别：
  - 在通用模式下，可能包含多余符号；可在后处理阶段做格式校验与清洗（可按需添加）。
- 格式/语言包：
  - 确认 `tesseract --list-langs` 含 `chi_sim`；否则需安装中文语言包。
- 断点续跑：
  - 脚本会生成 `ocr_temp_batch_*.csv` 作为中间文件，最后自动合并并按 `filename` 去重。

## 参数与定制（可按需调整）
- 在 `mass_ocr_to_excel.py` 顶部可修改：
  - `IMAGE_DIR`：图片目录。
  - `ROI_CONFIG_PATH`：当前使用的 ROI 配置文件路径（默认 `roi_config.json`）。
  - `LANG`：默认中文 `chi_sim`，脚本会组合英文以适配混合文本。
  - `MAX_WORKERS`、`BATCH_SIZE`：并发与分批参数。

## 示例输出（CSV）
```
filename,username,name,number
PAD_丁书芹_21556.jpg,丁书芹,丁书,RPAD000123060236
PAD_于世玲_21363.jpg,于世玲,于世玲,RPAD000123060043
LIN YU HAN_3775.jpg,,LIN YU HAN,PE ALLIC 9099
```

## 变更记录（近期）
- 批量识别支持按 ROI 裁剪识别，并导出为多列。
- 新增 `username` 列，从文件名提取中文姓名作为参考。
- 统一通用识别：去除 `name/number` 的字符白名单与语言限制，改用中英组合识别。

## 反馈与定制
如需：
- 多模板自动选择配置（按文件名前缀映射）；
- 每列自定义识别参数（`psm/lang` 等）；
- 特定字段格式校验与自动纠错；
请告知需求，我可以进一步扩展脚本实现。
