import functools
import traceback

from werkzeug.wsgi import ClosingIterator


__all__ = 'AfterResponse',


class AfterResponse:
    def __init__(self, app=None):
        self.callbacks = []
        if app:
            self.init_app(app)

    def __call__(self, callback):
        self.callbacks.append(callback)
        return callback

    def init_app(self, app):
        # install extension
        app.after_response = self

        # install middleware
        app.wsgi_app = AfterResponseMiddleware(app.wsgi_app, self)

    def flush(self, path_info: str):
        for fn in self.callbacks:
            try:
                fn(path_info)
            except Exception:
                traceback.print_exc()


class AfterResponseMiddleware:

    def __init__(self, application, after_response_ext):
        self.application = application
        self.after_response_ext = after_response_ext

    def __call__(self, environ, after_response):
        iterator = self.application(environ, after_response)
        try:
            return ClosingIterator(iterator, [
                functools.partial(
                    self.after_response_ext.flush,
                    path_info=environ['PATH_INFO']
                )
            ])
        except Exception:
            traceback.print_exc()
            return iterator
