#!/usr/bin/env python3
# usage: tools/s2title.py "title1" "title2" ... -> S2 match: title, year, venue, DOI, arXiv, abstract (first 900 chars)
import sys,json,time,urllib.request,urllib.parse
for t in sys.argv[1:]:
    u='https://api.semanticscholar.org/graph/v1/paper/search/match?query='+urllib.parse.quote(t)+'&fields=title,year,venue,externalIds,abstract,citationCount,authors'
    for k in range(4):
        try:
            d=json.load(urllib.request.urlopen(u,timeout=30)); break
        except Exception as e:
            d={'error':str(e)}; time.sleep(3+3*k)
    for p in d.get('data',[])[:1]:
        ids=p.get('externalIds') or {}
        print(f"### {p['title']} ({p.get('year')}; {p.get('venue')}; cites {p.get('citationCount')}) DOI={ids.get('DOI')} arXiv={ids.get('ArXiv')}\n AUTH: {', '.join(a['name'] for a in p.get('authors',[])[:6])}\n ABS: {(p.get('abstract') or 'NONE')[:900]}\n")
    if 'error' in d: print('### ERR',t,d['error'])
    time.sleep(1.2)
