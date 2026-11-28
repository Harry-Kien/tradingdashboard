"""Check Git's exact staged snapshot for private runtime files and credentials.

Optional --private-config is local-only; findings report file names, never values.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
TEXT={'.py','.json','.md','.txt','.bat','.js','.ts','.css','.html','.yml','.yaml','.toml'}
TOKENS=(r'sk-ant-[A-Za-z0-9_-]{20,}',r'sk-proj-[A-Za-z0-9_-]{25,}',r'ghp_[A-Za-z0-9]{25,}',
        r'github_pat_[A-Za-z0-9_]{30,}',r'\b[0-9]{8,12}:AA[A-Za-z0-9_-]{30,}',
        r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')


def private_markers(config):
    result=set()
    def walk(value):
        if isinstance(value,dict):
            for k,v in value.items():
                if isinstance(v,(str,int)) and re.search(r'token|api.?key|secret|password|mat_khau|chat.?id|login|tai_khoan',k,re.I) and len(str(v))>=6:
                    result.add(str(v))
                walk(v)
        elif isinstance(value,list):
            for item in value:walk(item)
        elif isinstance(value,str) and re.search(r'[A-Za-z]:[\\/]',value):
            result.add(os.path.expandvars(value))
    walk(config)
    return result


def inspect(path,body,markers=()):
    p=Path(path);parts=p.parts
    forbidden=(parts[0] in ('out','du-lieu','dist','pine') or p.name=='cau-hinh.json'
               or p.suffix.lower() in ('.sqlite','.sqlite3','.db','.jsonl','.log','.bak','.pkl','.npy')
               or (p.name.startswith('.env') and p.name!='.env.example'))
    if forbidden:return 'private_runtime_file'
    if p.suffix.lower() not in TEXT:return None
    text=body.decode('utf-8',errors='replace')
    if any(re.search(pattern,text) for pattern in TOKENS):return 'credential_pattern'
    low=text.casefold()
    if any(q.casefold() in low for v in markers for q in (v,v.replace('\\','\\\\'),v.replace('\\','/'))):
        return 'private_config_marker'
    return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-config',type=Path)
    args=parser.parse_args()
    markers=private_markers(json.loads(args.private_config.read_text(encoding='utf-8'))) if args.private_config else set()
    files=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf-8').split('\0')
    found=[]
    for name in filter(None,files):
        body=subprocess.check_output(['git','show',':'+name],cwd=ROOT)
        kind=inspect(name,body,markers)
        if kind:found.append({'file':name,'kind':kind})
    print(json.dumps({'files':len(list(filter(None,files))),'findings':found,'secret_values_in_output':False},ensure_ascii=False))
    return int(bool(found))


if __name__=='__main__':raise SystemExit(main())
