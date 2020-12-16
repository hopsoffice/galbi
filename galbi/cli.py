import json
import os
import pathlib
import typing
import urllib.parse

from click import argument, command, group, option, echo
from requests import Session, Response


__all__ = 'main',
default_config_directory = pathlib.Path(os.path.expanduser('~/.config/galbi'))
default_config_json = default_config_directory / 'config.json'
github_api_url = 'https://api.github.com/'


def load_config(p: pathlib.Path) -> dict:
    with p.open('r') as f:
        return json.loads(f.read())


@group()
def main():
    """Galbi CLI"""


@command()
@option('--repo', help='GitHub configuration repo', required=True,
        prompt='GitHub repo')
@option(
    '--token', help='GitHub personal access token', required=True,
    prompt='Your GitHub personal access token'
)
@option(
    '--refresh',
    default=False,
    is_flag=True,
)
def init(token: str, repo: str, refresh: bool):
    if not default_config_directory.exists():
        default_config_directory.mkdir()
    config_path = default_config_directory / 'config.json'
    if config_path.exists() and not refresh:
        echo('Skipping... {!s} is already exists'.format(config_path))
        return
    with config_path.open('w') as f:
        f.write(json.dumps({
            'token': token,
            'repo': repo,
        }))
    echo('Initialize galbi.')


def get_http_session(token_path: pathlib.Path) -> Session:
    with token_path.open('r') as f:
        payload = json.loads(f.read())
        token = payload['token']
    http = Session()
    http.headers.update({
        'Authorization': f'token {token}',
    })
    return http


def get_issue(label: str) -> typing.List[dict]:
    config = load_config(default_config_json)
    http = get_http_session(default_config_json)
    repo = config['repo']
    resp = http.get(
        urllib.parse.urljoin(github_api_url, f'/repos/{repo}/issues'),
        params={
            'state': 'open',
            'labels': label,
        }
    )
    resp.raise_for_status()
    return resp.json()


@command()
@option('--key', '-k')
@option('--value', '-v')
def deploy_key(key: str, value: str):
    config = load_config(default_config_json)
    deploy_kv_to_issue(config, key, value, filename='deploy_key.json')


def deploy_kv_to_issue(
    config: dict, key: str, value: str,
    *, filename: typing.Optional[str]=None
):
    repo = config['repo']
    http = get_http_session(default_config_json)
    label = http.get(
        urllib.parse.urljoin(github_api_url, f'/repos/{repo}/labels/{key}')
    )
    created = None
    if label.status_code == 200:
        issues = get_issue(key)
        for issue in issues:
            if issue['title'] == key:
                created = issue
                break
    else:
        resp = http.post(
            urllib.parse.urljoin(github_api_url, f'/repos/{repo}/labels'),
            json={'name': key}
        )
        resp.raise_for_status()
    if created is not None:
        url = created['comments_url']
    else:
        resp = http.post(
            urllib.parse.urljoin(github_api_url, f'/repos/{repo}/issues'),
            json={
                'title': key,
                'body': f'created from {filename}',
                'labels': [key]
            }
        )
        resp.raise_for_status()
        url = resp.json()['comments_url']
    resp = http.post(url, json={
        'body': json.dumps(value),
    })
    resp.raise_for_status()
    echo(f'"{key}" deploy done...')


@command()
@argument('filename', envvar='FILENAME', type=pathlib.Path)
def deploy(filename: str):
    config = load_config(default_config_json)
    with open(filename, 'r') as f:
        raw_file = f.read()
        payload = json.loads(raw_file) 
    echo('depoy start...')
    for k, v in payload.items():
        deploy_kv_to_issue(config, k, v, filename=filename)
    echo(f'Deploy done.')


def fetch_all_pages(
    fetch_func: typing.Callable[[int, int], Response]
) -> typing.Iterator[dict]:
    loadable = True
    page = 0
    per_page = 100
    while loadable:
        resp = fetch_func(page, per_page)
        resp.raise_for_status()
        payload = resp.json()
        if per_page > len(payload):
            loadable = False
        for item in payload:
            yield item
        page += 1


@command()
@option('--key', '-k', multiple=True)
def get(key: typing.List[str]):
    config = load_config(default_config_json)
    http = get_http_session(default_config_json)
    repo = config['repo']
    cache = {}
    keys = {x for x in key}
    issues = fetch_all_pages(
        lambda page, per_page: http.get(
            urllib.parse.urljoin(github_api_url, f'/repos/{repo}/issues'),
            params={
                'state': 'open',
                'page': page,
                'per_page': per_page,
            }
        )
    )
    for d in issues:
        if not keys:
            break
        if d['title'] in keys:
            keys.remove(d['title'])
            latest_comment = None
            for comment in fetch_all_pages(
                lambda page, per_page: http.get(
                    d['comments_url'],
                    params={
                        'per_page': per_page,
                        'page': page,
                    }
                )
            ):
                latest_comment = comment
            else:
                cache[d['title']] = json.loads(
                    latest_comment['body']
                )
    echo(json.dumps(cache, indent=4))


main.add_command(init)
main.add_command(deploy)
main.add_command(deploy_key)
main.add_command(get)


if __name__ == '__main__':
    main()
