// Shared by the Mac and Windows About drawer. Keep both languages equivalent.
export const ABOUT_COPY={
 en:[
  {title:'Created for learning',text:'AniCanto is a hobby project by SCKC. It began with a simple wish: to help the developer’s children learn Chinese characters and everyday Hong Kong Cantonese by listening to Cantonese dialogue while reading Chinese subtitles. Through animation, the project explores technology-assisted language learning and introduces the expression and culture of Hong Kong Cantonese to audiences around the world.'},
  {title:'Local AI, offline after setup',text:'AniCanto uses local language and voice models. Once the required models and runtimes are downloaded and ready, recognition, translation, dubbing and movie export run on your computer without an internet connection. Initial setup, new model downloads, repairs and updates require internet access.'},
  {title:'Respect for professional voice performers',text:'AniCanto is a tool for personal learning and creative experimentation. It is not intended to replace professional voice performers, and its AI-generated dubbing does not meet the standard of professional performance. We respect the training, creativity and dedication behind the craft—from interpreting a character and conveying emotion to shaping rhythm, pronunciation and dramatic intent. The value of that human artistry deserves recognition and support.'},
  {title:'Listen, read and compare',text:'The app supports Cantonese and English dubbing, original Japanese audio, and switchable Cantonese, English and combined bilingual subtitles. AI translation and speech generation may contain errors, accents, missing lines or incomplete performances; quality varies with the models and source material. These features are offered as an aid to exploration and learning, rather than a substitute for professionally produced dubbing.'}
 ],
 'zh-HK':[
  {title:'為學習而創作',text:'AniCanto 是由 SCKC 開發的興趣項目，最初的想法很簡單：希望家中的小朋友能夠一邊聆聽香港廣東話，一邊閱讀中文字幕，接觸日常口語並學習中文字。項目以動畫為媒介，探索科技輔助語言學習的可能，並讓世界各地的觀眾認識香港廣東話的表達方式與文化。'},
  {title:'本機 AI，部署後可離線使用',text:'AniCanto 使用本機語言及語音模型。所需模型與執行環境下載並準備好之後，辨識、翻譯、配音同影片匯出都喺你部電腦處理，毋須連線。首次部署、新增模型、修復下載同更新則需要網絡。'},
  {title:'尊重專業配音員',text:'AniCanto 旨在提供個人學習與創作實驗的輔助工具，並非取代專業配音員；本程式的 AI 配音亦無法達到專業演繹的水準。我們尊重配音員背後的訓練、創意與付出，從角色理解、情感表達，到節奏、發音與戲劇意圖的掌握，每一環都體現專業表演的價值，值得被認同與支持。'},
  {title:'聆聽、閱讀與比較',text:'程式支援廣東話及英文配音、日文原聲，以及可切換的廣東話、英文和中英雙語字幕。AI 翻譯與語音生成可能出現錯譯、口音、漏句或不完整演繹，效果亦取決於所選模型與來源素材。這些功能旨在協助探索與學習，並不等同於專業製作的配音作品。'}
 ]
};
export function aboutCopy(language){return ABOUT_COPY[language==='en'?'en':'zh-HK'];}
