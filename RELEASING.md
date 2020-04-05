# Releasing

```bash
rm dist/*
conda activate python3
python setup.py sdist bdist_wheel
twine upload dist/*
```
