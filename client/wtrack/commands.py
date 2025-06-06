import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from . import api_client as api
from . import auth
from .visualizer import plot_data

WEIGHT_UNIT = 'kg'

typer.core.rich = None

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    epilog="You're not fat, you're fluffy."
)

console = Console(width=120)


@app.command('login')
def login():
    with console.status('Signing in...'):
        auth.acquire_token()

    console.print('Signed in.')


@app.command('logout')
def logout():
    auth.logout()
    console.print('Signed out.')


@app.command('status')
def show_status():
    with console.status('Checking status...'):
        access_token = auth.acquire_token()
        response = api.get_status(access_token)

    if response['addedForToday']:
        console.print('[green]Weight data already added for today.[/]')
    else:
        console.print('[red]Weight data not added for today.[/]')

    missed = response['missedInLast30Days']
    console.print(f'{missed} entries missed in the last 30 days.')


@app.command('add')
def add_weight_data(
    weight: Annotated[float, typer.Argument()],
    date: Annotated[str, typer.Option('-d', '--date')] = None
):
    with console.status('Adding data...'):
        access_token = auth.acquire_token()
        api.add_weight_data(date, weight, access_token)

    console.print('Data added.')


@app.command('get')
def get_weight_data(
    date_from: Annotated[str, typer.Option('--from')] = None,
    date_to: Annotated[str, typer.Option('--to')] = None,
    limit: Annotated[int, typer.Option('--limit', help='Show only n last records in table')] = 10,
    plot: Annotated[bool, typer.Option('--plot')] = False
):
    with console.status('Fetching data...'):
        access_token = auth.acquire_token()
        response = api.get_weight_data(date_from, date_to, access_token)

    weight_data = response['data']

    if not weight_data:
        console.print('No data found.')
        return

    table = _create_weight_data_table(weight_data, limit)

    console.print()
    console.print(f"Weight unit: [bright_cyan]{WEIGHT_UNIT}[/]")
    console.print(table)

    console.print("Displayed:", min(len(weight_data), limit))
    console.print("Total received:", len(weight_data))

    max_value = response['max']
    min_value = response['min']
    avg_value = response['avg']

    console.print(f"\nMax: [bright_cyan]{max_value:>6.2f}[/] {WEIGHT_UNIT}")
    console.print(f"Min: [bright_cyan]{min_value:>6.2f}[/] {WEIGHT_UNIT}")
    console.print(f"Avg: [bright_cyan]{avg_value:>6.2f}[/] {WEIGHT_UNIT}")

    min_date = weight_data[0]['date']
    max_date = weight_data[-1]['date']

    console.print(f"\nDate range: [bright_cyan]{min_date}[/] - [bright_cyan]{max_date}[/]\n")

    if plot:
        plot_data(weight_data, max_value, min_value, avg_value)


@app.command('update')
def update_weight_data(
    date: Annotated[str, typer.Argument()],
    weight: Annotated[float, typer.Argument()]
):
    with console.status('Updating data...'):
        access_token = auth.acquire_token()
        api.update_weight_data(date, weight, access_token)

    console.print('Data updated.')


@app.command('remove')
def remove_weight_data(
    date: Annotated[str, typer.Argument()]
):
    with console.status('Removing data...'):
        access_token = auth.acquire_token()
        api.delete_weight_data(date, access_token)

    console.print('Data removed.')


def _create_weight_data_table(weight_data: list[dict], limit: int):
    table = Table()

    table.add_column('Date')
    table.add_column('Weight', justify='right')
    table.add_column('+/-', justify='right')

    data_chunk = weight_data[-limit:]

    for index, item in enumerate(data_chunk):
        diff = item['weight'] - data_chunk[index - 1]['weight'] if index > 0 else 0
        diff = f'[deep_pink2]+{diff:.2f}[/]' if diff > 0 else f'{diff:.2f}'
        table.add_row(item['date'], f'{item['weight']:.2f}', diff)

    return table
