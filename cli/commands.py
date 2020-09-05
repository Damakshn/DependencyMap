import click

@click.group()
def dpm():
    pass

@dpm.command()
def scan():
    print("Scan")

@dpm.command()
def view():
    print("view")

@dpm.command()
def export():
    print("export")
