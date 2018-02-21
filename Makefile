COMMIT_HASH = $(shell git log -n 1 --pretty=format:"%H")

test: clean virtualenv
		. env/bin/activate && python setup.py pytest

virtualenv:
		virtualenv ./env

clean:
		rm -rf ./env ./dist ./build ./artifacts ./dbsnap_verify.egg-info

build: clean virtualenv
		. env/bin/activate && python setup.py install

build-lambda: build
	    mkdir ./artifacts
		cp aws_lambda.py ./dist
		cp -rf env/lib/python2.7/site-packages/* ./dist
		cd ./dist && zip -r "../artifacts/lambda-dbsnap-verify-$(COMMIT_HASH).zip" .
