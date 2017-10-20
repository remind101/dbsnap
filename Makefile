DATE = $(shell date +%Y-%m-%d)

test: build
		. env/bin/activate
		pip install -r requirements-dev.txt
		py.test

clean:
		rm -rf ./env ./dist ./build

build:
		virtualenv ./env
		. env/bin/activate
		python setup.py install

build-lambda: build
		cp aws_lambda.py ./dist
		cp -rf env/lib/python2.7/site-packages/* ./dist
		cd ./dist && zip -r "../lambda-dbsnap-verify-$(DATE).zip" .
