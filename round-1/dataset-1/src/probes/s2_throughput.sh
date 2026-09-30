#!/bin/bash
# 30 S2 bulk calls spaced 1.1s, with backoff on 429
qs=("deep learning" "quantum dot" "metamaterial" "optogenetics" "graphene oxide" "microbiome" "crispr" "blockchain" "exome sequencing" "perovskite solar cell")
start=$(date +%s.%N); ok=0; n429=0
for i in $(seq 0 29); do
  q=${qs[$((i%10))]}; qq=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote('\"'+sys.argv[1]+'\"'))" "$q")
  while true; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "https://api.semanticscholar.org/graph/v1/paper/search/bulk?query=$qq&fields=year&sort=publicationDate:asc&year=1995-2018")
    if [ "$code" = "200" ]; then ok=$((ok+1)); break; fi
    n429=$((n429+1)); sleep 2
  done
  sleep 1.1
done
end=$(date +%s.%N)
echo "ok=$ok n429=$n429 elapsed=$(python3 -c "print($end-$start)") rate=$(python3 -c "print(30/($end-$start))")"
