DATE = $(shell date +%Y-%m-%d)

test: clean virtualenv
		. env/bin/activate && python setup.py pytest

virtualenv:
		virtualenv ./env

clean:
		rm -rf ./env ./dist ./build ./dbsnap_verify.egg-info

build: clean virtualenv
		. env/bin/activate && python setup.py install

build-lambda: build
		cp aws_lambda.py ./dist
		cp -rf env/lib/python2.7/site-packages/* ./dist
		cd ./dist && zip -r "../lambda-dbsnap-verify-$(DATE).zip" .
