python setup.py --command-packages=stdeb.command sdist_dsc

rm -r tmp
rm -r deb_build
mkdir tmp
cd tmp
dpkg-source -x ../deb_dist/pathomx_3.0.0a4-1.dsc
cd pathomx-3.0.0a4

debuild -S -sa
dput ppa:mfitzp/pathomx ../pathomx_3.0.0a4-1_source.changes
#dput ppa:mfitzp/pathomx deb_dist/pathomx_3.0.0a4-1.changes
