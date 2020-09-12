# Releasing

1. Update the versions in:
    - [setup.py](setup.py)
    - [badge-pypi-website.svg](docs/badge-pypi-website.svg)
2. Build the plugin:
    ```bash
    rm dist/*
    conda activate python3
    python setup.py sdist bdist_wheel
    ```
3. Upload to PyPI:
    ```bash
    twine upload dist/*
    ```
3. Tag in git
    ```bash
    git tag <version>
    git push origin <version>
    ```
5. Create the release in [Github Issues](https://github.com/dubreuia/visual_midi/releases)

