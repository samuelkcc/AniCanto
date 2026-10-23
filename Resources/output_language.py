"""Desktop output-language contract, shared with iPad's yue / zh / en codes."""
import re,subprocess
LANGUAGES={'yue':('香港廣東話','Hong Kong Cantonese','yue'),'zh':('普通話','Mainland Mandarin','zho'),'en':('英文','English','eng')}
def field(language):return {'yue':'cantonese','zh':'mandarin','en':'english'}[language]
def decision(language):return {'yue':'cantonese','zh':'mandarin','en':'english'}[language]
def target(language):return {'yue':'natural spoken Hong Kong Cantonese in Traditional Chinese','zh':'natural Mainland China spoken Mandarin in Simplified Chinese, using Mainland vocabulary and phrasing, not Cantonese or Taiwan wording','en':'natural spoken English'}[language]
def simplified(cfg,text):
 if not text:return text
 if cfg.get('executable'):return subprocess.check_output([cfg['executable'],'--simplified-text'],input=text.encode(),timeout=30).decode()
 try:
  from opencc import OpenCC
  return OpenCC('t2s').convert(text)
 except ImportError:return text

def validate_mandarin(text):
 return isinstance(text,str) and bool(re.search(r'[\u3400-\u9fff]',text)) and not re.search(r'[\u3040-\u30ff]|```|<think>|[\[【]',text) and not any(w in text for w in ('我哋','你哋','佢哋','唔係','冇嘢','點解','喺度')) and len(text)<1800
