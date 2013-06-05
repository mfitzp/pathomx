#!/bin/sh

cp originals/*.gif .
mogrify -crop -0-20 +repage *.gif
mogrify -alpha copy -channel alpha -negate +channel -fx '#000' -format png *.gif

rm *.gif

cp *.png 1
cp *.png 2
cp *.png 3
cp *.png 4
cp *.png 5
cp *.png 6
cp *.png 7
cp *.png 8
cp *.png 9


cd 1
mogrify +level-colors '#b2182b', *.png
cd ../2
mogrify +level-colors '#d6604d', *.png
cd ../3
mogrify +level-colors '#f4a582', *.png
cd ../4
mogrify +level-colors '#fddbc7', *.png
cd ../5
mogrify +level-colors '#ccc', *.png
cd ../6
mogrify +level-colors '#d1e5f0', *.png
cd ../7
mogrify +level-colors '#92c5de', *.png
cd ../8
mogrify +level-colors '#4393c3', *.png
cd ../9
mogrify +level-colors '#2166ac', *.png