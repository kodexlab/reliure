# Makefile for reliure

.PHONY: help tests clean doc testall testdoc

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  help    prints this help"
	@echo "  doc     build doc + tests"
	@echo "  test    runs unit tests"
	@echo "  testlib runs doctests on lib only"
	@echo "  testall runs all tests doc+rst"
	@echo "  testcov runs coverage unit tests"
	@echo "          $ py.test --cov PATH_OR_FILE --cov-report term-missing"

clean-doc:
	rm -rf docs/_build/ docs/_templates/

doc: testdoc
	make -C ./docs html

publish-doc:
	rm -rf ./doc/_build/
	make -C ./docs html
	scp -r ./docs/_build/html/* 192.168.122.99:/var-hdd/www-proxteam/doc/reliure/

test:
	py.test -v ./tests --cov reliure --cov-report html

testlib: 
	py.test -v ./reliure --doctest-module 

testdoc:
	py.test -v ./docs --doctest-glob='*.rst'

testall: 
	py.test -v ./tests ./reliure --doctest-module --cov reliure --cov-report html

testcov:
	py.test --cov reliure --cov-report term-missing

clean:
	# removing .pyc filesin
	find ./ -iname *.pyc | xargs rm
	find ./ -iname *.py~ | xargs rm

all: help
