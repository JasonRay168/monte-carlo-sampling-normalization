for f in $(ls *.svg)
do
  rsvg-convert -f eps "$f" -o "${f%.svg}.eps"
done