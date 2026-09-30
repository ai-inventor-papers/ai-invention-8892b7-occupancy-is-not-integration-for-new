#!/usr/bin/env python3
# usage: tools/s2cites.py <label> <DOI> [citations|references] -> snowball/<label>_<dir>.json (all pages, title/year/abstract/ids)
import sys,json,time,urllib.request,pathlib
lab,doi=sys.argv[1],sys.argv[2]; dr=sys.argv[3] if len(sys.argv)>3 else 'citations'
key='citingPaper' if dr=='citations' else 'citedPaper'
out=[];off=0
while True:
    u=f'https://api.semanticscholar.org/graph/v1/paper/{doi}/{dr}?fields=title,year,abstract,externalIds,venue&limit=1000&offset={off}'
    for k in range(6):
        try: d=json.load(urllib.request.urlopen(u,timeout=60)); break
        except Exception as e: d=None; time.sleep(5+5*k)
    if not d: print('FAIL at',off); break
    out+= [x[key] for x in d.get('data',[])]
    if 'next' not in d or not d.get('data'): break
    off=d['next']; time.sleep(1.5)
p=pathlib.Path(__file__).parent.parent/'snowball'/f'{lab}_{dr}.json'; p.write_text(json.dumps(out))
print(lab,dr,len(out))
