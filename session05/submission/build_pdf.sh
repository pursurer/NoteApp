#!/bin/zsh
# Build the Class 5 lab reports: Markdown -> standalone HTML (pandoc) -> PDF (headless Chrome).
set -euo pipefail
here=${0:A:h}
out=${here:h:h:h}/output/pdf
chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
mkdir -p "$out" "$here/build"
for name in Lab1-Transit-Audit Lab2-Password-Audit; do
  pandoc "$here/$name.md" --standalone --embed-resources --resource-path="$here" \
    --css="$here/report.css" --metadata lang=en -o "$here/build/$name.html"
  "$chrome" --headless=new --disable-gpu --no-pdf-header-footer \
    --print-to-pdf="$out/Class05-$name.pdf" "file://$here/build/$name.html" 2>/dev/null
  cp "$out/Class05-$name.pdf" "$here/Class05-$name.pdf"
  echo "wrote $out/Class05-$name.pdf (copy in $here)"
done
