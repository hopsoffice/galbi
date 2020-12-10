# Galbi

Less important configuration management system.

## Installation

### Requires

- Python 3.6 +
- GitHub personal access token: <https://github.com/settings/tokens>


### Install dependencies

```console
$ pip install -e .
```


### Initialize configuration

```console
$ galbi init
GitHub repo: ...
Your GitHub personal access token: ...

Initialize galbi.
```


## How to deploy key?

It uploads json to reposotory's issue.

```console
$ galbi deploy something.json

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
