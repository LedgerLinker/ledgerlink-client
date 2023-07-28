from invoke import task


@task
def typecheck(c):
    """Run the mypy static analysis."""
    c.run('mypy --config-file mypy.ini ledgerlinker')


@task#(typecheck)
def test(c):
    "Run nostests and generate coverage report."""
    c.run('python -m pytest --cov-report xml:cov.xml --cov', pty=True)


@task
def build_dist(c):
    """Steps to build and package supergsl as library for pypi."""
    c.run('pip install twine')
    c.run('rm -rf build dist')
    c.run('python setup.py sdist bdist_wheel')
    c.run('twine check dist/*')
    c.run('echo "Build complete, run \'twine upload dist/*\' to upload to pypi."')
