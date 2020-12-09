import json
import os
import pathlib
import urllib.parse
import webbrowser

from click import argument, command, group, option, echo
from flask import Flask, request
from requests import Session

from .crypto import encrypt, decrypt
from .wsgi_util import AfterResponse


__all__ = 'main',
default_config_directory = pathlib.Path(os.path.expanduser('~/.config/galbi'))
default_config_json = default_config_directory / 'config.json'
default_config_token = default_config_directory / 'token'


def read_server_url(config: pathlib.Path) -> str:
    with config.open('r') as f:
        payload = json.loads(f.read())
    return payload['server']


@group()
def main():
    """Galbi CLI"""


@command()
@option(
    '--server', help='Galbi server.', required=True,
    prompt='Your galbi server'
)
@option(
    '--config-dir',
    default=default_config_directory,
    type=pathlib.Path,
    help='Galbi configuration directory.',
    prompt='Your configuration directory?'
)
def init(server: str, config_dir: pathlib.Path):
    parsed = urllib.parse.urlparse(server)
    assert parsed.scheme and parsed.netloc, f'"{server}" is not an url.'
    config_path = config_dir / 'config.json'
    if not config_dir.exists():
        config_dir.mkdir()
    if config_path.exists():
        echo('Skipping... {!s} is already exists'.format(config_path))
        return
    with config_path.open('w') as f:
        f.write(json.dumps({
            'server': server,
        }))
    echo('Initialize galbi.')


@command()
@option(
    '--port',
    help='Galbi port.',
    default=5012
)
@option(
    '--config-dir',
    default=default_config_directory,
    type=pathlib.Path,
    help='Galbi configuration directory.',
)
@option(
    '--refresh',
    default=False,
    is_flag=True,
)
def authorize(port: int, config_dir:pathlib.Path,
              refresh: bool):
    token_path = config_dir / 'token'
    if token_path.exists() and not refresh:
        echo('Already has the token...')
        # TODO token valid process
        return
    app = Flask(__name__ + 'flask')
    after_response = AfterResponse()
    after_response.init_app(app)

    @app.after_response
    def exit(path_info):
        if path_info == '/token':
            echo('Save token! You may close the browser...')
            os._exit(0)

    @app.route('/token', methods=['GET'])
    def token():
        token = request.args.get('token')
        if token:
            with token_path.open('w') as f:
                f.write(token)
            return 'Authorize done. You may close the browser.'
        else:
            return 'Something goes wrong...'

    echo('Login github on your browser,')
    echo('\nRunning webserver to get token...\n')
    server = read_server_url(config_dir / 'config.json')
    base_url = urllib.parse.urljoin(server, '/login')
    webbrowser.open(base_url + f'?port={port}')
    app.run(port=port)


def get_http_session(token_path: pathlib.Path) -> Session:
    with token_path.open('r') as f:
        token = f.read()
    http = Session()
    http.headers.update({
        'X-Galbi-Token': token,
    })
    return http


@command()
@argument('filename', envvar='FILENAME', type=pathlib.Path)
@option(
    '--config',
    default=default_config_json,
    type=pathlib.Path,
    help='Galbi configuration file.',
)
@option(
    '--token',
    default=default_config_token,
    type=pathlib.Path,
    help='Galbi configuration directory.',
)
@option(
    '--secret-key',
    type=pathlib.Path,
    help='ssh secret key',
    required=True,
)
def deploy(filename: str, token: pathlib.Path, config: pathlib.Path,
           secret_key: pathlib.Path):
    http = get_http_session(token)
    server = read_server_url(config)
    with open(filename, 'r') as f:
        raw_file = f.read()
        json.loads(raw_file) 
    url = urllib.parse.urljoin(server, f'/deploy/{filename}')
    response = http.post(url, json={
        'data': encrypt(raw_file),
    })
    assert response.status_code == 200
    echo(f'Run \'galbi get {filename}\' to get config.')


@command()
@argument('filename', envvar='FILENAME')
@option(
    '--config',
    default=default_config_json,
    type=pathlib.Path,
    help='Galbi configuration file.',
)
@option(
    '--token',
    default=default_config_token,
    type=pathlib.Path,
    help='Galbi configuration directory.',
)
@option(
    '--public-key',
    type=pathlib.Path,
    help='ssh public key',
)
def get(filename: str, token: pathlib.Path, config: pathlib.Path,
        public_key: str):
    http = get_http_session(token)
    server = read_server_url(config)
    url = urllib.parse.urljoin(server, f'/config/{filename}')
    response = http.get(url, json=filename)
    assert response.status_code == 200
    payload = response.json()
    print(payload)
    echo(json.dumps(json.loads(decrypt(payload['data'])), indent=2))


main.add_command(init)
main.add_command(authorize)
main.add_command(deploy)
main.add_command(get)


if __name__ == '__main__':
    main()
