# AniCanto 桌面版技术支持

[English](SUPPORT.md) · [繁體中文](SUPPORT.zh-HK.md) · [简体中文](SUPPORT.zh-CN.md) · [日本語](SUPPORT.ja.md)

[主页及部署](README.zh-CN.md) · [当前流程](docs/DESKTOP-WORKFLOW-0.25.0.md)

此仓库由 SCKC 提供 **macOS／Windows 桌面开源版本**。桌面使用、部署问题和反馈请提交到[问题列表](https://github.com/samuelkcc/AniCanto/issues)。

## 报告桌面问题

[新建报告](https://github.com/samuelkcc/AniCanto/issues/new?title=%5BDesktop%5D%20)，请提供：

1. AniCanto 版本／build、操作系统版本。
2. CPU、系统 RAM、显卡及 VRAM，注明 CPU、Apple Metal／MLX 或 NVIDIA CUDA。
3. 翻译、识别及配音模型、字幕来源类型，以及启用的修复选项。
4. 重现步骤、预期结果、实际错误、最后阶段／句数及等待时间。
5. 必要时附上已删除个人信息的诊断片段或截图。

请先搜索已有报告，同一问题在原 issue 继续回复。技术支持不要求赞助。

## 常见检查

- **部署失败：** 检查空间、内存估算、运行环境和相关模型下载。检测到硬件不代表所有显卡和模型都已验证。
- **转换慢或暂停：** 查看最新阶段和句数；关闭前先暂停保存，然后续跑。百分比不变不一定表示卡住。
- **字幕／配音问题：** 注明内置文字字幕、外挂 SRT／ASS／SSA／VTT 或画面 OCR，并提供时间点；逐句比较原声、分离声与配音。
- **测试新流程：** 暂停的旧任务保留原设置。请重置测试视频或创建新转换，以使用新默认规则。
- **成品：** 删除项目或录音前，确认所选输出文件夹中的视频能够正常播放。

## 公开报告与内容

报告是公开的。发布日志前请移除私人路径、账号、视频、录音、文稿和个人信息，不需要提供完整私人媒体。

模型和运行环境准备后，默认转换在本机进行；下载及更新需要联网。云端文件夹同步由所选存储服务处理。支持页及问题列表由 GitHub 托管，适用 [GitHub 隐私声明](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement)。仅处理有权使用的视频、字幕及声线参考。
