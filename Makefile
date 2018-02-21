COMMIT_HASH = $(shell git log -n 1 --pretty=format:"%H")

clean:
		rm -rf ./env ./dist ./build ./artifacts ./dbsnap_verify.egg-info

### Python3 ###

test: clean virtualenv
		. env/bin/activate && python setup.py pytest

virtualenv:
		virtualenv ./env

build: clean virtualenv
		. env/bin/activate && python setup.py install

build-lambda: build
	    mkdir ./artifacts
		cp aws_lambda.py ./dist
		cp -rf env/lib/python*/site-packages/* ./dist
		cd ./dist && zip -r "../artifacts/lambda-dbsnap-verify-$(COMMIT_HASH).zip" .

### Python3 ###

test3: clean venv
		. env/bin/activate && python setup.py pytest

venv:
		python3 -m venv env && env/bin/pip install setuptools --upgrade

build3: clean venv
		. env/bin/activate && python setup.py install

build-lambda3: build3
	    mkdir ./artifacts
		cp aws_lambda.py ./dist
		cp -rf env/lib/python*/site-packages/* ./dist
		cd ./dist && zip -r "../artifacts/lambda-dbsnap-verify-$(COMMIT_HASH).zip" .
