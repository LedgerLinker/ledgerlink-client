from invoke import task


@task
def typecheck(c):
    """Run the mypy static analysis."""
    c.run('mypy --config-file mypy.ini ledgerlinker')


@task#(typecheck)
def test(c):
    "Run nostests and generate coverage report."""
    c.run('python -m pytest --cov-report xml:cov.xml --cov', pty=True)
