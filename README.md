# Galbi

Less important configuration management system.

## Installation

### Requires

- Python 3.6 +
- GitHub personal access token: <https://github.com/settings/tokens>


### Install

Recommend to use [pipx][] to install command line interface in isolated
environment.

```console
$ pip install pipx
$ pipx install galbi
```

[pipx]: https://github.com/pipxproject/pipx


### Initialize configuration

```console
$ galbi init
GitHub repo: ...
Your GitHub personal access token: ...

Initialize galbi.
```


## How to deploy key?

It uploads JSON to reposotory's issue.

```console
$ galbi deploy something.json

...
```

<img src="./images/issue_list.png" />

JSON key should be a title and label of issue.

<img src="./images/issue_detail.png" />

JSON value added to comment of the issue. Latest comment is the configuration
value of JSON key.

If someone deploy the same JSON key, value pair, It adds comment on the issue.

For deploying a single configuration, It supports `deploy-key` command.

```console
$ galbi deploy-key -k foo  -v bar
...
```

## How to get key?

```
$ galbi get --key foo --key bar
{
    "foo": ...,
    "bar": ...,
}
```

Note that galbi only get a configuration from an opened issue.
If you want to deprecate/remove the configuration, close the issue.
