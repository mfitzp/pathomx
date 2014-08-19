call "C:\Program Files (x86)\Microsoft Visual Studio 11.0\VC\bin\x86_amd64\vcvarsx86_amd64.bat"
SET VS90COMNTOOLS=%VS110COMNTOOLS%
rem python setup.win.py bdist_msi
python -m nsist installer.win.cfg