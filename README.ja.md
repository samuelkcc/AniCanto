[繁體中文](README.md) · [English](README.en.md) · [简体中文](README.zh-CN.md) · **日本語**

<p align="center"><img src="docs/images/anicanto-cantonese-cover.png" alt="AniCanto — original Cantonese studio assistants" width="1100"></p>

# AniCanto

**あなたのアニメに、新しい声を。**

日本のアニメのセリフを**香港広東語または英語の吹き替え**に変換します。モデルと実行環境の準備後は、認識・翻訳・音声生成・書き出しをすべてローカルで実行します。

## Beta をダウンロード · 0.24.58

**[Mac 版](https://github.com/samuelkcc/AniCanto/releases/download/v0.24.58-beta/AniCanto-macOS-0.24.58.zip)** · **[Windows 版](https://github.com/samuelkcc/AniCanto/releases/download/v0.24.58-beta/AniCanto.exe)** · [更新内容と対応するソース](https://github.com/samuelkcc/AniCanto/releases/tag/v0.24.58-beta)

## パソコンの推奨構成

**推奨音声モデル：完全版 Drama 3。** 翻訳には Qwen 3.5 を使用し、64 GB Mac では 35B、32 GB RAM の Windows では小さめの 9B が選択肢です。開発者の試聴では Drama 3 が香港広東語に近い発音でしたが、元音声や場面によって結果は異なります。

| 環境 | 推奨システム・メモリ | Drama 3 の実行方法 |
| --- | --- | --- |
| **Mac** | Apple Silicon、macOS 14 以降。**64 GB 以上のユニファイドメモリを推奨** | 完全版 4-bit MLX。Apple Silicon GPU／ユニファイドメモリを使用。推定約 28 GB |
| **Windows** | Windows 10／11 x64。**RAM 32 GB 以上、64 GB なら余裕あり** | 完全版 GGUF Q2 を **CPU で実行**。システム RAM は推定約 22 GB |

**Windows の Drama 3 は、現在 NVIDIA／AMD／Intel GPU による高速化に対応していません。** 独立 GPU があっても Drama 3 は CPU とシステム RAM を使用します。他の対応モデルでは GPU を使用できる場合がありますが、VRAM は Drama 3 に必要な RAM の代わりにはなりません。この Windows パッケージの実機テストは別途必要です。

32 GB Mac でも小さな翻訳モデルとの組み合わせを試せますが、Drama 3 によりスワップ、大幅な速度低下、読み込み失敗が起こる場合があります。メモリ値は計画用の推定です。モデル・実行環境・作業ファイル用に **100 GB 以上の空き容量**を推奨します。長い動画には追加容量が必要です。

## 今回の Beta

- 動画をキュー順に連続処理。未開始の動画は並べ替え可能。
- 字幕の読み込みを「字幕ソース」に集約。校正項目を確認済み・後で確認に分類。
- 基本モードのプレビューを縮め、進捗と試聴を上に配置。Mac／Windows の「一時停止して保存」は赤色に統一。

## 3 ステップで開始

1. アプリをダウンロードして開き、モデルと実行環境を準備します。初期設定にはインターネット接続が必要です。
2. 動画を追加し、広東語・英語・両方から選択。外部字幕はプレビュー上部の **字幕ソース → 字幕ファイルを読み込む**（SRT／ASS／SSA／VTT）から追加できます。
3. 処理を開始して完成動画を再生。気になる箇所は校正レポートで元音声・分離音声・吹き替えを比較し、再生成または過去の録音を選んで別バージョンを書き出せます。

[字幕読み込みガイド](docs/ja/GETTING-STARTED.md)

## 現在のアプリ画面

0.24.58 の実際の UI にオリジナルのデモ素材とモデル・プロジェクトの例を表示しています。処理性能の測定結果ではありません。

### ようこそ・セットアップ

![ようこそ・セットアップ](docs/images/welcome-ja.png)

### 基本モード：進捗と試聴

![基本モード：進捗と試聴](docs/images/basic-ja.png)

### エキスパートモード：タイムラインと編集

![エキスパートモード：タイムラインと編集](docs/images/timeline-ja.png)

### 校正レポート：問題と録音の比較

![校正レポート：問題と録音の比較](docs/images/review-ja.png)

[すべての画面を見る](docs/ja/SCREENSHOTS.md)

## 使用前に

AI ではアクセント、誤訳、単語の欠落、声質の変化が生じる場合があります。重要な場面は試聴してください。字幕は意味の確認を補助し、日本語音声を主な根拠にします。元音声・広東語・英語の個別トラックと OP／ED の保持に対応し、結果は場面によって異なります。

SCKC の趣味のプロジェクトです。独自コードは MIT、第三者のコンポーネントとモデルはそれぞれのライセンスに従います。Built with Fish Audio。Drama 3 は Fish Audio Community License 1.0 を使用します。利用権限のある動画・字幕・音声のみを処理してください。

[プロジェクトを応援](https://buymeacoffee.com/samuelchen) · [MIT](LICENSE) · [Licences](docs/LICENSING.md)
