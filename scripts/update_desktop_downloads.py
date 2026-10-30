"""Synchronize all desktop homepages from the released-platform download record."""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
START='<!-- desktop-downloads:start -->'
END='<!-- desktop-downloads:end -->'
PAGES={
 'README.md':('Download','Mac','Windows','Release notes','Source materials','Source backup and rebuild guide'),
 'README.en.md':('Download','Mac','Windows','Release notes','Source materials','Source backup and rebuild guide'),
 'README.zh-HK.md':('下載','Mac','Windows','版本說明','對應源碼','源碼備份及重建說明'),
 'README.zh-CN.md':('下载','Mac','Windows','版本说明','对应源码','源码备份及重建说明'),
 'README.ja.md':('ダウンロード','Mac','Windows','リリースノート','対応ソース','ソースの保管と再ビルド'),
}
def render(config,labels):
 title,mac,windows,notes,source,rebuild=labels
 base='https://github.com/'+config['repository']+'/releases'
 versions={key:config[key]['version'] for key in ('mac','windows')}
 for value in versions.values():
  if not re.fullmatch(r'\d+\.\d+\.\d+',value):raise ValueError('Invalid released version')
 urls={key:f"{base}/download/v{versions[key]}-beta/{config[key]['asset']}" for key in versions}
 release=f"{base}/tag/v{versions['windows']}-beta"
 sources=f"{base}/download/v{versions['windows']}-beta/available-source-materials.tar.gz"
 return (START+'\n<a id="download"></a>\n\n## '+title+'\n\n'
  +f"**[{mac} {versions['mac']}]({urls['mac']})** · **[{windows} {versions['windows']}]({urls['windows']})**\n\n"
  +f'[{notes}]({release}) · [{source}]({sources}) · [{rebuild}](docs/BUILD-AND-RECOVERY.md)\n'+END)
def sync(root=ROOT,check=False):
 config=json.loads((root/'docs/DESKTOP-DOWNLOADS.json').read_text());changed=[]
 for name,labels in PAGES.items():
  path=root/name;before=path.read_text()
  pattern=re.escape(START)+r'.*?'+re.escape(END)
  after,count=re.subn(pattern,lambda _:render(config,labels),before,flags=re.S)
  if count!=1:raise ValueError('Expected one download block: '+name)
  if before!=after:
   changed.append(name)
   if not check:path.write_text(after)
 if check and changed:raise ValueError('Download links are out of sync: '+', '.join(changed))
 return dict(pages=list(PAGES),mac=config['mac']['version'],windows=config['windows']['version'],changed=changed,check=check)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args();print(json.dumps(sync(check=args.check)))
