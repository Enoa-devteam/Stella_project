# Windows 安装、升级与启动

中文 | [English](windows-install.en.md) · [文档总览](../README.md)

本页面向 **Windows 桌面**部署。Linux / 远程服务器请直接看 [Docker 部署指南](deployment-docker.md)。

> **v2 控制面（现行界面）**：浏览器直接访问 Bot 同端口即是完整管理面板（鉴权/配置/插件/MCP/知识库/定时任务/实时日志，详见 [WebUI 管理](webui.md)）；桌面壳（Tauri 2）内嵌同一套面板。旧版原生界面已淘汰，冻结于 tag `gui-v1-final`。

## 当前版本注意事项（6.4.4）

- 6.4.4：新增 OneBot V12（实验性，尚未对接真实实现验证，QQ 请继续用 V11）；运行时安装器拒绝会写到运行时目录之外的 ZIP 条目；渲染依赖要求 playwright ≥ 1.65.2（已安装的环境下次需要渲染时可能重新下载浏览器内核，约 270MB）。
- 6.4.3 起：Online 安装器首次启动下载运行时与组件期间显示加载视图（动态 Logo、实时进度与已用时），不再显示「后端未运行」与重试按钮（[#145](https://github.com/Enoa-devteam/stella_project/issues/145)）。
- 6.4.2 起：修复 Online 安装器在干净的 Windows 上下载组件报 `CERTIFICATE_VERIFY_FAILED`（v6.0.1–v6.4.1 受影响），下载中途断线改为续传重试。
- 6.4.1 起：没有 Visual C++ 运行库的 Windows 上桌面程序与随包 llama.cpp 后端可以启动，全新安装首次启动不再失败。
- Online 安装器从 GitHub 与 Hugging Face 下载组件，尚无镜像；无法稳定访问时请使用 Offline 安装器（约 1.2 GB）。
- 安装器未经代码签名：开启「智能应用控制」的 Windows 11 会直接拦截。
- 自 6.4.0 起：记忆 schema 为 24（回退须恢复迁移前备份）、不再内置 NapCat、不再发布 stella CLI 包、暂时只安装 OneBot V11 适配器。

升级前备份完整数据根；从旧目录导入时先运行 `python -m deploy migrate --from <旧目录> --dry-run`。完整变更见 [发布说明](../../release_assets/RELEASE_NOTES_TEMPLATE.md)。

## 环境要求

| 组件 | 要求 |
|---|---|
| 操作系统 | Windows 10/11 x64（缺 WebView2 时：OneClick Offline 内置离线安装器，OneClick Online 联网下载；Standalone 需系统自带） |
| Python | 3.10+（OneClick 安装包内置嵌入式 Python；Standalone 解压版需自装） |
| 框架 | [NoneBot 2](https://nonebot.dev/) |
| QQ 协议端 | [NapCat](https://github.com/NapNeko/NapCatQQ) 或其他 OneBot V11 实现（需自行安装并扫码登录；安装包自 2026-11 起不再内置 NapCat） |
| 模型服务 | 可选的本地 [LM Studio](https://lmstudio.ai/) / `llama.cpp` Runtime，或任意 OpenAI 兼容的在线 API（填地址 + API key 即可），两者可混用；也可以关闭 AI |

## 📦 下载与安装

- 第一步：到 [Releases](https://github.com/Eternal-Wanderer-Vegetable/stella_project/releases) 选一种 Windows 产品下载。按「要不要帮你把运行环境装好」分两条产品线：

  - **OneClick 一键安装（推荐）**：`Stella-OneClick-Python-vX.Y.Z-windows-amd64.exe`，单文件安装程序，双击安装。首次启动会自动准备嵌入式 Python、`llama.cpp` CPU 后端与 `qwen3-embedding-0.6b` 向量模型。**自 2026-11 起安装包不再内置 NapCat**（上游安装包下载源已失效），QQ 协议端需自行安装（见下方「接入 QQ」）。想用 Rust 记忆引擎就下载 `Stella-OneClick-Rust-vX.Y.Z-windows-amd64.exe`，引擎在安装阶段一并就绪。
  - **OneClick 一键安装·离线版**：`Stella-OneClick-Python-Offline-vX.Y.Z-windows-amd64.exe`（Rust 版为 `Stella-OneClick-Rust-Offline-*`）。安装流程与在线版完全相同，但嵌入式 Python、全部 Python 依赖、`llama.cpp` CPU 后端、NapCat、向量模型与浏览器渲染内核**全部随包内置，安装与渲染全程不需要联网**——适合国内网络受限或内网环境。代价是安装包体积约 1GB。
  - **Standalone 解压版**：`Stella-Standalone-Python-vX.Y.Z-windows-amd64.zip`，解压即用，**只包含 stella 本体**——需要自备 Python 3.10+ 与 NapCat，也不会自动下载 `llama.cpp` 或任何模型。Rust 版（`Stella-Standalone-Rust-*.zip`）额外附带 Rust 记忆引擎 wheel，首次启动自动离线安装并启用。

  两类产品都提供 `Stella.exe` 图形界面（推荐）与 `start.bat` 命令行两种启动方式。`Stella.exe` 启动时自动跑一遍环境自检——尚未配置会打开「配置」页，有阻塞问题会打开「环境自检」页，一切正常则直接进入「运行状态」页；`start.bat` 则进入命令行配置向导并启动 Bot。**请勿把两类产品装进同一个目录。**

> **关于「未知发布者」提示**：当前版本的 Windows 安装程序尚未做代码签名（签名证书就绪后会恢复强制签名门禁），SmartScreen 可能弹出「未知发布者」警告，属预期行为。每个 Release 附带 `SHA256SUMS.txt` 可自行校验下载完整性；下载页的说明与发布工作流是唯一可信来源。

> AI 可以关闭。关闭 AI 或本地模型暂不可用时，基础 Bot、OneBot 诊断和部署管理仍可运行。

- 第二步：按使用场景准备其余组件：

  - 接入 QQ：OneClick 与 Standalone 都需先自行安装并登录 [NapCat](https://github.com/NapNeko/NapCatQQ) 或其他 OneBot V11 实现（登录需人工扫码），再在 NapCat WebUI 的「网络配置」里添加「WebSocket 客户端」指向 Bot（反向 WS，地址 `ws://127.0.0.1:8080/onebot/v11/ws`）。
  - 如果要使用本地聊天模型：安装 [LM Studio](https://lmstudio.ai/) 并加载模型（OneClick 已内置 `llama.cpp` CPU 后端与向量模型）。使用在线模型时不需要安装 LM Studio。

> **小提示**：首次运行会下载并运行 Python，此行为可能会被您电脑上的安全防护软件报告为可疑操作并拦截，需加入信任列表。

- 第三步：
  - 1.首次打开 `Stella.exe` 后会出现配置界面。先填**监听端口**（就是第二步在 NapCat 里配的反向 WS 端口）与要让 stella 进的**群号**。
  - 2.往下到「模型服务」分区，按你的部署方式点一个**一键预设**，再把对应的端点卡片填完：
    - **全本地** → 点「纯本地」，在本机 OpenAI 兼容端点卡片里填 LM Studio、llama.cpp 或其他兼容服务的地址与模型 ID。点卡片上的「测试连接」可以读取服务端模型列表。
    - **全在线 / 混合** → 点「纯在线（双 key）」或「混合（对话在线 · 整合本地）」，在两张在线卡片里各填一次服务商地址、API key 与模型 ID。**两把 key 要填不同的**，原因见[三种部署模式](../reference/configuration.md#三种部署模式)。
  - 3.配置完成后，单击“保存并检查”，程序会自动跳转至“运行状态”界面。单击“启动”即可。

> 遇到了问题？你可以加入开发者所在的QQ群：263402786，在群里@（目前唯一的）开发者Eternal-Wanderer-Vegetable。

## 配置

建议使用 `Stella.exe` 中内置的“高级选项”表单来进行修改。**不建议手动修改.env。**

完整配置项及其说明见 **[配置参考](../reference/configuration.md)**。

## 启动

在 `Stella.exe` 的「运行状态」页点「启动」（会先跑一遍 doctor 自检）；或双击 `start.bat` 走命令行流程。在群里 @ 机器人即可开始对话。

从源码启动开发实例见 [环境准备](../development/environment.md#启动开发实例)。装插件见 [插件安装](plugins.md)。出问题先看 [排查问题](../development/troubleshooting.md)。

## ⬆️ 从旧版本升级

1. 运行 `stop.bat` 停止程序
2. OneClick：直接运行新版本的安装程序；Standalone：把新版本解压到一个新目录
3. 双击 `Stella.exe`（或 `start.bat`）→ 确认「配置导入」

配置、记忆、人格、空间设置与已装插件会自动搬过来，数据库自动升级，`runtime/` 自动复用（省一次
约 100MB 的下载）。全程**只读旧目录**——无论成败旧安装都还在原地能跑，可以放心重试；导入报告
写在当前 `STELLA_HOME/migration_report.md`。命令行等价操作：

```bash
python -m deploy migrate --dry-run   # 先看预览（会在数据库副本上真跑一遍）
python -m deploy migrate             # 执行
```

OneClick 安装还可以用版本化升级做**原子切换**：`python -m deploy upgrade <已解包的新版本目录> --version X.Y.Z` 校验通过后切换激活记录；出问题 `python -m deploy upgrade --rollback` 一键回滚到保留的上一版本树（双向）。

版本化升级工具与安装器默认布局是两回事：当前发布工作流 `VERSIONED_LAYOUT=0`，不会默认开启 launcher 搬移路径；适用条件见 [源码合同](../development/contracts.md)。

从 2.x 升级也不需要丢记忆：旧库会自动迁移（列改名、按共享空间重新归属、用户画像归入其消息
最多的那个空间）。

## 用户数据放在哪

取决于产品线与安装历史（`python -m deploy paths` 可查看实际位置与命中的规则）：

- **OneClick 全新安装**：数据根默认放在**程序目录之外**的 `%LOCALAPPDATA%\stella\Data`，机器级指针文件 `%LOCALAPPDATA%\stella\home.txt` 记录这个位置——卸载重装、升级换程序目录都不会碰到数据。已有的数据根（旧版同级目录、便携目录、指针指向）一律沿用，**绝不迁移**。
- **Standalone 与手工部署**：默认放在程序目录**同级**的 `StellaData/`：

```text
D:\你的目录\
  stella\                ← 程序目录（升级时整个换掉，可以放心删；Standalone 压缩包内没有
                            内层文件夹，解压目标就是它）
  StellaData\            ← 你的数据（升级时一动不动）
```

- **便携模式（两条产品线通用）**：想让程序与数据自包含（整体拷进 U 盘），在程序目录里手工建一个 `StellaData\` 子目录即可，程序会优先用它——代价是它会跟着程序目录一起被替换或删除，升级前务必先导入或备份。

此后升级只需替换程序目录，数据不用动；清理旧的版本文件夹不会碰到数据。数据根的完整解析规则见 [配置参考 · 两个根目录](../reference/configuration.md#两个根目录程序目录与数据目录)。
