# 操作系统支持矩阵

| 系统 | 状态 | 负责人 | 说明 |
|---|---|---|---|
| Windows 10/11 | ✅ MVP 完整支持 | - | 双击 `scripts/start_windows.bat` 或根目录 `start.bat` |
| macOS | 🚧 实验性 | 待认领 | `scripts/start_macos.sh` 为占位，欢迎贡献 |
| Linux | 🚧 实验性 | 待认领 | `scripts/start_linux.sh` 为占位，欢迎贡献 |
| Docker | 🚧 可选 | 待认领 | 当前未提供可用镜像或 compose 配置 |

## 如何贡献某系统支持

1. 完善对应 `scripts/start_xxx` 脚本，覆盖虚拟环境、依赖检查、启动和错误提示。
2. 更新 `app/services/deps.py` 中该系统的安装提示。
3. 在 `.github/workflows/ci.yml` 中为该系统启用测试 job；修绿后移除该 job 的 `continue-on-error`。
4. 更新本文件的支持矩阵和 README 安装说明。
5. 验证核心文件操作使用 `pathlib.Path`，子进程调用传入参数列表且未使用 `shell=True`。
