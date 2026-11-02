const COPY={
  "Subtitle first": {
    "zh-HK": "字幕優先",
    "zh-CN": "字幕优先",
    "ja": "字幕優先"
  },
  "Speech first": {
    "zh-HK": "語音優先",
    "zh-CN": "语音优先",
    "ja": "音声優先"
  },
  "Speech / OCR": {
    "zh-HK": "語音 / OCR",
    "zh-CN": "语音 / OCR",
    "ja": "音声 / OCR"
  },
  "Subtitle language": {
    "zh-HK": "字幕語言",
    "zh-CN": "字幕语言",
    "ja": "字幕の言語"
  },
  "Use selected subtitles": {
    "zh-HK": "使用所選字幕",
    "zh-CN": "使用所选字幕",
    "ja": "選択した字幕を使用"
  },
  "Other language": {
    "zh-HK": "其他語言",
    "zh-CN": "其他语言",
    "ja": "その他の言語"
  },
  "Choose the subtitle source and language. Chinese captions are used for Cantonese or Mandarin. English output prefers English, then Chinese.": {
    "zh-HK": "請選擇字幕來源及語言。廣東話或普通話輸出使用中文字幕；英文輸出先選英文，再選中文。",
    "zh-CN": "请选择字幕来源及语言。粤语或普通话输出使用中文字幕；英语输出先选英语，再选中文。",
    "ja": "字幕ソースと言語を選んでください。広東語・標準中国語には中国語字幕を使用します。英語出力は英語、次に中国語を優先します。"
  },
  "Automatic uses Subtitle first when readable subtitles exist, otherwise Speech first. Speech / OCR ignores embedded and imported subtitles. Speech always supplies dubbing timing.": {
    "zh-HK": "自動偵測有可讀取字幕時使用「字幕優先」，否則使用「語音優先」。「語音 / OCR」忽略內置及匯入字幕。配音時間一律按原聲定位。",
    "zh-CN": "自动检测有可读取字幕时使用“字幕优先”，否则使用“语音优先”。“语音 / OCR”忽略内置及导入字幕。配音时间始终按原声定位。",
    "ja": "自動検出は読める字幕があれば「字幕優先」、なければ「音声優先」を使用します。「音声 / OCR」は内蔵・取り込み字幕を無視します。吹き替えの時刻は元の音声で決めます。"
  }
};
export function sourceModesTranslation(text,language){return COPY[text]?.[language]||null}
