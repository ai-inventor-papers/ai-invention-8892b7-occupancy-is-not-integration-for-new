#!/usr/bin/env python3
# usage: tools/g.py <name> <regex> [context=300] [max=10]  -- case-insensitive grep over cache/<name>.md
import re,sys,pathlib
name,pat=sys.argv[1],sys.argv[2]; ctx=int(sys.argv[3]) if len(sys.argv)>3 else 300; mx=int(sys.argv[4]) if len(sys.argv)>4 else 10
t=(pathlib.Path(__file__).parent.parent/'cache'/f'{name}.md').read_text(errors='ignore')
ms=list(re.finditer(pat,t,re.I|re.S)); print(f'## {name} /{pat}/ {len(ms)} matches')
for m in ms[:mx]: print(f'@{m.start()}: ...'+re.sub(r'\s+',' ',t[max(0,m.start()-ctx):m.end()+ctx])+'...\n--')
