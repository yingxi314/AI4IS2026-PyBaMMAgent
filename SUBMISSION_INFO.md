# 仿真软件 Agent 接入挑战赛提交说明

姓名：  
软件名：PyBaMM

## 功能

1. Multi-model Battery Simulation Comparison
2. C-rate Parameter Sweep
3. Charge-discharge Cycle Protocol Simulation
4. Automatic Engineering KPI Extraction
5. Physical Consistency and Operating-window Validation

## 基本功能说明

本项目实现了 PyBaMM 开源电池仿真软件的 Agent 接入。用户可以通过自然语言向 Agent 下达任务，Agent 在本地自动解析意图和参数，并调用 PyBaMM 执行真实锂离子电池仿真，自动提取结果并生成数据文件、可视化图表、Markdown 分析报告、运行日志和验证材料。项目不调用在线大模型 API，仿真结果不是假数据。

## 复现方式

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
bash scripts/run_demo.sh
python3 scripts/check_submission.py
```

## 主要附件内容

- `agent/`：Agent 主程序、自然语言解析和 PyBaMM 工作流
- `cases/`：标准电池仿真测试案例配置
- `scripts/`：一键运行、后处理、验证和提交检查脚本
- `outputs/`：主仿真时序结果、性能摘要和自然语言解析摘要
- `reports/`：可视化图表、数据表与 Markdown 分析报告
- `logs/`：自然语言调用日志和运行元数据
- `README.md`：环境配置、功能说明与运行命令
- `EXTENSIONS.md`：5 项扩展功能及对应证据文件
