# Roadmap & Downstream Conventions

*从 findings.md 迁移，2026-03-05*

---

## 长期路线图（待实现）

### Phase 4A+：FoodAI 接入（等待审批）
- 食物场景从 Gemini 切换为 FoodAI（SG 本土，756类 100+本地菜）+ SeaLION 文字建议
- 状态：FoodAI v5.0 Trial 已申请（2026-02-23），等待约 5 工作日审批
- 涉及文件：新建 `llm/foodai.py`、修改 `nodes/food_analyzer.py`、`config.py`

### Phase 4B：营养 MCP 接入（提升食物精度）
- VLM 识别菜名 -> MCP Tool 查精确营养值（替代 VLM 估算）
- 推荐：`deadletterq/mcp-opennutrition`（30万+食物，本地运行，无隐私问题）
- 涉及文件：`nodes/food_analyzer.py`、`schemas/outputs.py`（加 data_source 字段）

### Phase 4C：RxNorm 药物验证（免费）
- VLM 提取药名 -> RxNorm API 标准化验证
- API：`https://rxnav.nlm.nih.gov/REST/drugs?name=Metformin`（完全免费，20次/秒）
- 涉及文件：新建 `tools/rxnorm.py`、`nodes/medication_reader.py`、`schemas/outputs.py`

### Phase 5：进阶方向（长期/演示）
- NUS FoodSG-233 — 233种SG本地菜数据集（209,861张图片）
- AWS Textract + Comprehend Medical — 报告数字化增强
- HPB FOCOS 本地营养数据库 RAG

---

## 下游协作约定

### null 字段 = 图片中该信息不存在（不是识别失败）
下游节点应据此触发用户追问：

| 场景 | 缺失字段 | 下游触发示例 |
|------|---------|------------|
| 药物 | frequency | "这个补剂没有标注服用频次，你通常怎么吃？" |
| 药物 | dosage | "照片上看不清剂量，能确认一下是多少 mg 吗？" |
| 食物 | quantity | "这份看起来是鸡饭，你吃了多少？整份还是半份？" |

### confidence 使用约定
| 值 | 建议下游行为 |
|----|------------|
| >= 0.8 | 直接使用，无需确认 |
| 0.5~0.8 | 展示结果但请用户确认 |
| < 0.5 | 不自动使用，主动询问 |

### schema 设计原则
- 字段存在即可信（非 null = VLM 实际识别到）
- null = 信息源本身没有（不是错误）
- scene_type 是路由键，下游可直接 switch

---

## 未来方向（暂不实现，记录思路）

### 提取完整度信号（Completeness Signal）

**背景**：下游 chatbot 需要知道"这次识别质量怎样"，以决定是否直接使用结果或追问用户。

**现有机制**：null 字段已经隐式传递了"信息缺失"的信号（null = 图片中不存在该信息）。

**未来可以增强**：
```json
"missing_fields": ["dosage", "frequency"],
"completeness": 0.4
```

**何时做**：等 chatbot 模块开始真正消费 Vision 输出时，再根据实际需求设计。
