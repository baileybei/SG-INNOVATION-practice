# Vision Agent - SG INNOVATION

**[English](README.md) | 中文**

AI 驱动的多模态 Vision Agent，面向新加坡慢性病管理。分析饮食照片、药物图片和医疗报告——将非结构化图片转化为结构化、可计算的数据。

隶属于 **SG INNOVATION** 比赛 —— 糖尿病患者慢病管理与社区平台。

## 架构

### LangGraph 流水线

```
[图片输入（1张或多张）]    支持多图（如药盒正面+背面、多页报告）
     |
[image_intake]        接收图片，逐个校验格式与大小，转 base64（上限 5 张）
     |
[scene_classifier]    场景分类：FOOD / MEDICATION / REPORT / UNKNOWN
     |
     +-- FOOD       → [food_analyzer]       识别菜品，估算营养数据
     +-- MEDICATION → [medication_reader]    提取药名、剂量、频次
     +-- REPORT     → [report_digitizer]     提取化验指标（HbA1c、血糖等）
     +-- UNKNOWN    → [rejection_handler]    拒识非目标图片
     |
[health_advisor]      基于识别结果，生成本地化健康建议（SeaLION）
     |
[output_formatter]    Pydantic 校验，统一 JSON 输出
     |
[结构化 JSON 输出]
```

### VLM 策略（模型层）

```
当前（开发阶段）：
  Gemini 2.5 Flash  →  视觉 + 文本分析（临时 VLM）
  SeaLION 27B Text  →  新加坡本地化健康建议

计划（生产环境）：
  FoodAI (A*STAR/SMU) →  "眼睛" - 新加坡食物识别（756 类，100+ 本地菜品）
  SEA-LION VL          →  "大脑" - 多语言分析 & 饮食建议
```

所有 VLM 实现共享 `BaseVLM` 抽象接口 —— 换模型只需改一行配置，无需修改图逻辑。

| 提供方 | 模型 | 状态 | 用途 |
|--------|------|------|------|
| `mock` | MockVLM | ✅ 可用 | 开发/测试，无 API 调用 |
| `gemini` | Gemini 2.5 Flash | ✅ 可用 | 临时 VLM，三场景通用 |
| `sealion` | Gemma-SEA-LION-v4-27B-IT | ✅ 可用 | 纯文本分析 & 健康建议 |
| `foodai` | FoodAI v5.0 | ⏳ 待批 | 新加坡食物识别（已申请） |

## 快速开始

### 1. 安装

```bash
git clone <repo-url>
cd SG_INNOVATION
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env，填入你的 API 密钥：
#   GEMINI_API_KEY=your_key
#   SEALION_API_KEY=your_key
```

### 3. 运行

```bash
# 使用 Gemini 分析（真实 VLM）
make run-gemini IMG=test_images/chicken_rice.jpg

# 使用 Mock 分析（无 API，开发/测试用）
make run IMG=test_images/sample.jpg

# 多图分析（如药盒正面+背面）
python -m src.vision_agent front.jpg back.jpg --provider gemini

# JSON 格式输出
make run-json IMG=test_images/sample.jpg PROVIDER=gemini

# 直接 CLI 调用
python -m src.vision_agent photo.jpg --provider gemini --json
```

### 4. 测试

```bash
make test              # 运行全部测试（171 个）
make coverage          # 测试 + 覆盖率报告（99%+）
```

## 项目结构

```
SG_INNOVATION/
├── README.md                            # 英文文档
├── README_CN.md                         # 中文文档
├── CLAUDE.md                            # AI 开发指南
├── plan.md                              # 项目计划 & 路线图
├── Makefile                             # make test / make run-gemini 等
├── requirements.txt
├── .env.example                         # 环境变量模板
│
├── src/vision_agent/
│   ├── agent.py                         # 公开 API：VisionAgent.analyze()
│   ├── graph.py                         # LangGraph 状态图定义
│   ├── state.py                         # 共享状态（TypedDict）
│   ├── config.py                        # .env 配置读取（Pydantic）
│   ├── logging_config.py
│   ├── __main__.py                      # CLI 入口
│   │
│   ├── llm/                             # VLM 接口层
│   │   ├── base.py                      # BaseVLM 抽象基类
│   │   ├── gemini.py                    # Google Gemini 2.5 Flash（当前）
│   │   ├── sealion.py                   # SEA-LION 文本模型
│   │   ├── mock.py                      # Mock（开发/测试用）
│   │   └── retry.py                     # 指数退避重试包装器
│   │
│   ├── nodes/                           # 图节点（处理步骤）
│   │   ├── image_intake.py              # 图片加载 & base64 编码
│   │   ├── scene_classifier.py          # 场景分类（4 类）
│   │   ├── food_analyzer.py             # 食物识别 & 营养估算
│   │   ├── medication_reader.py         # 药物信息提取
│   │   ├── report_digitizer.py          # 化验报告数字化
│   │   ├── health_advisor.py            # 健康建议生成（SeaLION）
│   │   ├── rejection_handler.py         # 非目标图片处理
│   │   └── output_formatter.py          # Pydantic 校验 & 格式化
│   │
│   ├── prompts/                         # 新加坡本地化 Prompt 模板
│   │   ├── classifier.py                # 场景分类 prompt
│   │   ├── food.py                      # 50+ 新加坡菜品，HPB 营养参考
│   │   ├── medication.py                # 新加坡药物，HSA 标签，BD/OD/TDS 解析
│   │   ├── report.py                    # MOH/HPB 参考范围，新加坡医院格式
│   │   └── advisor.py                   # 健康建议 prompt（饮食/药物/报告）
│   │
│   └── schemas/                         # Pydantic v2 输出模型
│       └── outputs.py                   # FoodOutput, MedicationOutput, ReportOutput
│
├── tests/                               # 171 个测试，覆盖率 99%+
│   ├── conftest.py                      # 共享 fixtures
│   ├── test_config.py
│   ├── test_graph.py
│   ├── test_nodes/
│   └── test_schemas/
│
└── test_images/                         # 测试图片（已 gitignore）
```

## 输出示例

### 饮食分析

```json
{
  "scene_type": "FOOD",
  "items": [
    {
      "name": "Hainanese Chicken Rice",
      "quantity": "1 plate",
      "nutrition": {
        "calories_kcal": 480.0,
        "carbs_g": 65.0,
        "protein_g": 28.0,
        "fat_g": 12.0,
        "sodium_mg": 820.0
      }
    }
  ],
  "total_calories_kcal": 480.0,
  "meal_type": "lunch",
  "confidence": 0.91
}
```

### 药物核查

```json
{
  "scene_type": "MEDICATION",
  "drug_name": "Metformin Hydrochloride",
  "dosage": "500mg",
  "frequency": "twice daily with meals (BD)",
  "route": "oral",
  "warnings": ["Do not crush or chew", "Take with food to reduce GI side effects"],
  "confidence": 0.87
}
```

### 医疗报告数字化

```json
{
  "scene_type": "REPORT",
  "report_type": "blood_test",
  "indicators": [
    {"name": "HbA1c", "value": "7.2", "unit": "%", "reference_range": "4.0-5.6", "is_abnormal": true},
    {"name": "Fasting Glucose", "value": "6.8", "unit": "mmol/L", "reference_range": "3.9-6.1", "is_abnormal": true}
  ],
  "report_date": "2024-01-15",
  "lab_name": "Singapore General Hospital",
  "confidence": 0.95
}
```

## API 用法

```python
from src.vision_agent.agent import VisionAgent
from src.vision_agent.llm.gemini import GeminiVLM

# 使用 Gemini（真实视觉分析）
agent = VisionAgent(vlm=GeminiVLM())
result = agent.analyze("meal_photo.jpg")

print(result.scene_type)        # "FOOD"
print(result.confidence)        # 0.91
print(result.as_food.items)     # [FoodItem(...), ...]

# 多图分析（如药盒正面+背面）
result = agent.analyze(["front.jpg", "back.jpg"])
print(result.is_multi_image)    # True
print(result.image_path)        # "front.jpg"（向后兼容）
print(result.image_paths)       # ["front.jpg", "back.jpg"]

# 使用 Mock（开发/测试，无 API 调用）
agent = VisionAgent()
result = agent.analyze("any_image.jpg")
```

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `VLM_PROVIDER` | 否 | `mock` | VLM 提供方：`mock`、`gemini`、`sealion` |
| `GEMINI_API_KEY` | provider=gemini 时 | - | Google Gemini API 密钥 |
| `SEALION_API_KEY` | provider=sealion 时 | - | SEA-LION API 密钥 |
| `LOG_LEVEL` | 否 | `INFO` | DEBUG, INFO, WARNING, ERROR |
| `VLM_MAX_RETRIES` | 否 | `3` | VLM 调用最大重试次数 |
| `VLM_RETRY_DELAY_S` | 否 | `1.0` | 重试初始延迟（秒） |
| `MAX_IMAGE_SIZE_MB` | 否 | `10.0` | 图片文件大小上限 |

## 技术栈

- **编排框架**: LangGraph（状态图编排）
- **语言**: Python 3.10+
- **视觉模型**: Gemini 2.5 Flash（临时）/ SEA-LION（计划）
- **数据校验**: Pydantic v2
- **HTTP 客户端**: httpx
- **测试**: pytest（171 个测试，覆盖率 99%+）

## 许可

SG INNOVATION 比赛项目 - AI Singapore
