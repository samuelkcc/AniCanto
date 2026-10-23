[繁體中文](README.md) · [English](README.en.md) · **简体中文** · [日本語](README.ja.md)

<p align="center"><img src="docs/images/anicanto-cantonese-cover.png" alt="AniCanto — original Cantonese studio assistants" width="1100"></p>

# AniCanto

**你的动画，另一种声音。**

将日本动画的日语对白转换成**香港粤语或英语配音**。安装所需模型和运行环境后，识别、翻译、配音和导出都在本机完成。

## 为什么会有 AniCanto

AniCanto 是 SCKC 从兴趣开始的小项目，初衷很简单：**希望孩子一边听日常香港粤语，一边看中文字幕，接触口语、学习汉字。** 给熟悉的动画换一种粤语声音，让看动画也成为探索语言的一点乐趣。

也希望把这份乐趣分享给对粤语感兴趣的人。你可以比较粤语、英语和原装日语，认识香港粤语的表达与文化。界面提供繁体中文、英语、简体中文和日语；配音输出支持粤语及英语。

## 下载 Beta · 0.24.58

**[下载 Mac 版](https://github.com/samuelkcc/AniCanto/releases/download/v0.24.58-beta/AniCanto-macOS-0.24.58.zip)** · **[下载 Windows 版](https://github.com/samuelkcc/AniCanto/releases/download/v0.24.58-beta/AniCanto.exe)** · [更新说明及对应源代码](https://github.com/samuelkcc/AniCanto/releases/tag/v0.24.58-beta)

## 先选择电脑配置

**首选配音模型：完整 Drama 3。** 翻译搭配 Qwen 3.5：64 GB Mac 建议使用 35B；32 GB RAM 的 Windows 可搭配 9B。开发者试听中，Drama 3 更接近香港粤语发音；实际效果仍受原声和场景影响。

| 平台 | 建议系统及内存 | Drama 3 运行方式 |
| --- | --- | --- |
| **Mac** | Apple Silicon、macOS 14+；建议 **64 GB 或以上统一内存** | 完整 4-bit MLX，使用 Apple Silicon GPU／统一内存；估算约 28 GB |
| **Windows** | Windows 10／11 x64；**32 GB RAM 起，64 GB 更充裕** | 完整 GGUF Q2 **使用 CPU**；估算约 22 GB 系统 RAM |

**Windows 版 Drama 3 目前不使用 NVIDIA／AMD／Intel GPU 加速。** 即使配备独立显卡，Drama 3 仍使用 CPU 和系统 RAM。其他支持的模型可按显卡和驱动使用 GPU；独立显存不能替代 Drama 3 所需的系统内存。这个 Windows 安装包仍需实机测试。

32 GB Mac 可以尝试较小的翻译模型组合，但 Drama 3 可能导致交换内存、明显变慢或加载失败。以上内存数字为规划估算。两个平台建议预留 **100 GB 以上**存储空间用于模型、运行环境和工作文件；长视频需要更多。

## 应用可以做什么

| 功能 | 如何使用 |
| --- | --- |
| **粤语／英语配音** | 选择单语或双语，在同一视频中保留独立音轨及字幕，通过兼容播放器切换。 |
| **中文字幕辅助核对** | 参考内置文字字幕、外挂字幕或画面 OCR，辅助理解人名和意思；日语音频仍是主要依据。 |
| **保留片头片尾** | 自动检测 OP／ED，默认保留日语歌曲和原声。 |
| **基本及专家模式** | 基本模式自动处理；专家模式提供时间轴、改稿、时间调整及逐句编辑。 |
| **试听、重录和校对** | 比较原声、分离声音和生成配音；逐句重录或选择旧录音，再导出新版，保留之前的成品。 |
| **本机批量处理** | 视频排队、调整未开始视频的顺序、暂停保存和继续；模型准备好后可离线运行。 |

## 支持格式

| 类别 | 格式 |
| --- | --- |
| **输入视频** | MP4 · MKV · MOV · M4V · AVI · WebM · TS |
| **外挂字幕** | SRT · ASS · SSA · VTT |
| **输出成品** | MP4，按所选设置加入音轨和字幕。 |

扩展名兼容仍需文件内的影音编码可以读取。画面内嵌字幕可尝试 OCR，但不保证能从画面中干净移除。

## 这个 Beta 新增了什么

- 按视频列表连续处理；尚未开始的视频可以调整顺序。
- 通过统一的“字幕来源”面板导入字幕；校对问题可标为已检查或稍后处理。
- 基本模式预览更紧凑，进度和试听位置更高；Mac／Windows 的“暂停并保存”统一为红色。

## 三步开始

1. 下载并打开应用，准备模型和运行环境；首次设置需要网络。
2. 添加视频，选择粤语、英语或双语。外挂字幕入口：预览上方 **字幕来源 → 导入字幕文件**（SRT／ASS／SSA／VTT）。
3. 开始处理并播放成品。如有疑问，在校对报告中逐句比较原声、分离声音和配音，重新生成或选择旧录音，再导出另一个版本。

[字幕导入说明](docs/zh-CN/GETTING-STARTED.md)

## 新版界面

以下为 0.24.58 真实界面，使用原创演示素材和示意模型／项目状态，不代表转换性能测试。

### 欢迎与部署

![欢迎与部署](docs/images/welcome-zh-CN.png)

### 基本模式：进度与试听

![基本模式：进度与试听](docs/images/basic-zh-CN.png)

### 专家模式：时间轴与逐句编辑

![专家模式：时间轴与逐句编辑](docs/images/timeline-zh-CN.png)

### 校对报告：问题与录音比较

![校对报告：问题与录音比较](docs/images/review-zh-CN.png)

[查看全部界面截图](docs/zh-CN/SCREENSHOTS.md)

## 使用前须知

AI 仍可能产生口音、误译、漏字或声线变化；重要场景请试听。字幕辅助核对意思，日语音频仍为主要依据。支持原声、粤语和英语独立音轨及 OP／ED 保留，效果因场景而异。

项目也通过失败片段不断改进：逐句试听、追查问题，再调整流程。AI 可以辅助检查，但对白是否自然、是否适合角色，仍需要人来听。

**配音是一门专业。** AniCanto 用于学习和创作实验，AI 的演绎仍有不足；希望大家继续欣赏和支持专业配音演员。

SCKC 的兴趣项目。原创代码采用 MIT，第三方组件和模型保留各自许可。Built with Fish Audio；Drama 3 使用 Fish Audio Community License 1.0。请只处理有权使用的视频、字幕和声音。

[支持项目](https://buymeacoffee.com/samuelchen) · [MIT](LICENSE) · [Licences](docs/LICENSING.md)
