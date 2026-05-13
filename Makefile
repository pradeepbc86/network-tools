.PHONY: install test lint clean

install:
	pip3 install -e .

test:
	pytest tests/ -v

lint:
	python3 -m py_compile netcli/cli.py netcli/config/generator.py netcli/peering/peeringdb.py netcli/rpki/validator.py netcli/inventory/collector.py netcli/console/connector.py && echo "All files OK"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf *.egg-info dist build
