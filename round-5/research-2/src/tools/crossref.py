#!/usr/bin/env python3
# usage: tools/crossref.py < dois.txt  -> one line per DOI: OK|doi|title|container|vol(issue):page|year|authors  (or FAIL)
import sys,json,time,urllib.request,urllib.parse
for doi in [l.strip() for l in sys.stdin if l.strip()]:
    u='https://api.crossref.org/works/'+urllib.parse.quote(doi)+'?mailto=aii-research@example.org'
    m=None
    for k in range(5):
        try: m=json.load(urllib.request.urlopen(u,timeout=30))['message']; break
        except urllib.error.HTTPError as e:
            if e.code==404: break
            time.sleep(2+3*k)
        except Exception: time.sleep(2+3*k)
    if m is None: print(f'FAIL|{doi}',flush=True); continue
    au=', '.join(a.get('family','') for a in m.get('author',[])[:5])
    print(f"OK|{doi}|{(m.get('title') or [''])[0][:100]}|{(m.get('container-title') or [''])[0][:45]}|{m.get('volume')}({m.get('issue')}):{m.get('page') or m.get('article-number')}|{m['issued']['date-parts'][0][0]}|{au}",flush=True)
    time.sleep(0.4)
