PYTHON=`which python`
NAME=`python setup.py --name`


all: check test source deb

init:
	pip install -r requirements.txt --use-mirrors

dist: source deb

source:
	$(PYTHON) setup.py sdist

deb:
	$(PYTHON) setup.py --command-packages=stdeb.command bdist_deb

rpm:
	$(PYTHON) setup.py bdist_rpm --post-install=rpm/postinstall --pre-uninstall=rpm/preuninstall

test:
	unit2 discover -s tests -t .
	python -mpytest weasyprint

check:
	find . -name \*.py | grep -v "^test_" | xargs pylint --errors-only --reports=n
	# pep8
	# pyntch
	# pyflakes
	# pychecker
	# pymetrics

clean: