import sys
import click
import settings
from dpm.node_repository import NodeRepository, RepositoryException
from dpm.graphsworks import DpmGraph
from sync.scanner import DpmScanner

repository = None


@click.group()
def dpm():
    global repository
    repository = NodeRepository.get_instance(settings.config)


@dpm.command()
def scan():
    scanner = DpmScanner(settings.config["connector"])
    scanner.load_applications(settings.config["applications"])
    scanner.load_databases(settings.config["databases"])
    scanner.run_scanning()


@dpm.command()
@click.option("-a", is_flag=True)
@click.option("-databases", is_flag=True)
@click.option("-apps", is_flag=True)
@click.option("-forms", is_flag=True)
@click.option("-components", is_flag=True)
@click.option("-tables", is_flag=True)
@click.option("-views", is_flag=True)
@click.option("-sp", is_flag=True)
@click.option("-tf", is_flag=True)
@click.option("-sf", is_flag=True)
@click.option("-tr", is_flag=True)
def view(a, databases, apps, forms, components, tables, views, sp, tf, sf, tr):
    global repository
    if a:
        databases = True
        apps = True
        forms = True
        components = True
        tables = True
        views = True
        sp = True
        tf = True
        sf = True
        tr = True
    # ToDo сортировка результата
    result = repository.get_nodes_by_class(databases, apps, forms, components, tables, views, sp, tf, sf, tr)
    # row_format = "{:6}    {:30}    {}"
    row_format = "{:6}    {:30}"
    click.echo(row_format.format("ID", "НАЗВАНИЕ"))
    # click.echo(row_format.format("ID", "НАЗВАНИЕ", "ПОЛНОЕ НАЗВАНИЕ"))
    for item in result:
        # click.echo(row_format.format(item.id, item.name, item.full_name))
        click.echo(row_format.format(item.id, item.name))


@dpm.command()
@click.option("-name", type=str)
@click.option("-id", type=int)
@click.option("-down", type=int, default=0)
@click.option("-up", type=int, default=0)
def export(name, id, up, down):
    global repository
    # region Проверки
    if (name is None and id is None):
        click.echo(click.style("Нужно указать либо имя, либо ID объекта", fg="red"))
        sys.exit(1)
    if (up == 0 and down == 0):
        click.echo(click.style("Не задано количество уровней зависимостей для загрузки", fg="red"))
        sys.exit(1)
    if (name is not None and id is not None):
        if not click.confirm(
            click.style(
                "Указаны одновременно имя и ID объекта. ID используется в приоритете. Продолжить?",
                fg="bright_yellow"
            )
        ):
            sys.exit(1)
    # endregion
    try:
        if id is not None:
            node_for_export = repository.get_node_by_id(id)
        else:
            node_for_export = repository.get_node_by_name(name)
    except RepositoryException as e:
        click.echo(click.style(str(e), fg="red"))
        sys.exit(1)
    g = DpmGraph(node_for_export)
    g.load_dependencies(levels_down=down, levels_up=up)
    g.export_to_gexf()
