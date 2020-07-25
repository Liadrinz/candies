from proto import *
from config import *

class Candy:
    
    def get_prefix(self, prefix):
        return list(filter(lambda m: m.startswith(prefix) and callable(getattr(self, m)), dir(self)))

    def get_decorators(self):
        return self.get_prefix('decorator_')
    
    def get_exports(self):
        return self.get_prefix('export_')

register = '''
for SubCandy in Candy.__subclasses__():
    singleton = SubCandy()
    for method in singleton.get_decorators() + singleton.get_exports():
        name = '_'.join(method.split('_')[1:])
        exec(f'{name} = singleton.{method}', globals(), locals())
'''

import time
import traceback

class _Exception(Candy):

    def decorator_catch_exception(self, func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                traceback.print_exc()
        return wrapper
    
    def decorator_ignore_exception(self, func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                pass
        return wrapper

exec(register)

from concurrent.futures import ThreadPoolExecutor

class _Concurrent(Candy):

    def __init__(self):
        self.pool = ThreadPoolExecutor(max_workers=threads)
        self.intervals = {}
    
    def _set_max_workers(self, value):
        self.pool._max_workers = value
    
    def task_wrapper(self, func, sleep, *args, **kwargs):
        @catch_exception
        def task():
            time.sleep(sleep)  # keep consistence
            return func(*args, **kwargs)
        return self.pool.submit(task)
    
    def interval_task_wrapper(self, func, name, sleep, *args, **kwargs):
        @catch_exception
        def task():
            while name in self.intervals:
                time.sleep(sleep)
                func(*args, **kwargs)
        return self.pool.submit(task)

    def export_clear_interval(self, name):
        if name in self.intervals:
            self.intervals.pop(name)

    def decorator_set_timeout(self, timeout=0):
        if callable(timeout):
            func = timeout
            def wrapper(*args, **kwargs):
                return self.task_wrapper(func, 0, *args, **kwargs)
        else:
            def wrapper(func):
                def inner_wrapper(*args, **kwargs):
                    return self.task_wrapper(func, timeout/1000, *args, **kwargs)
                return inner_wrapper
        return wrapper

    def decorator_set_interval(self, name, interval=0):
        if callable(interval):
            func = interval
            self.intervals[name] = 1
            def wrapper(*args, **kwargs):
                return self.interval_task_wrapper(func, name, 0, *args, **kwargs)
        else:
            def wrapper(func):
                self.intervals[name] = 1
                def inner_wrapper(*args, **kwargs):
                    return self.interval_task_wrapper(func, name, interval/1000, *args, **kwargs)
                return inner_wrapper
        return wrapper

exec(register)

class _Timer(Candy):

    def decorator_timer(self, prefix, factor=1, suffix='s'):
        def wrapper(func):
            def inner_wrapper(*args, **kwargs):
                begin = time.time()
                value = func(*args, **kwargs)
                print(f'{prefix}: {(time.time() - begin) * factor}{suffix}')
                return value
            return inner_wrapper
        return wrapper

class _AOP(Candy):

    def decorator_aop(self, before=None, after=None):
        def wrapper(func):
            def inner_wrapper(*args, **kwargs):
                if callable(before):
                    before(*args, **kwargs)
                value = func(*args, **kwargs)
                if callable(after):
                    after(*args, **kwargs)
                return value
            return inner_wrapper
        return wrapper

exec(register)

import re
import requests

from xml.sax.saxutils import unescape


class _HTTPData(Candy):

    def __init__(self):
        self.data = None
        self._cookies = None
        self._session = requests.Session()

    def export_result(self):
        return self.data

    def decorator_embed(self, func):
        exec(f'self.{func.__name__} = func', globals(), locals())

    def decorator_src(self, url, headers=None, data=None, method='get', mode='t', coding='utf-8', consumes=None, inherit_cookies=False, new_session=False):
        def wrapper(func):
            def inner_wrapper(*args, **kwargs):
                if new_session:
                    self._session = requests.Session()
                _url, _coding, _headers, _data = self._replace_all_params(kwargs, url, coding, headers, data)
                if _headers is None:
                    _headers = {}
                _headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.87 Safari/537.36'})
                if consumes is not None:
                    headers['Content-Type'] = consumes
                if method.lower() == 'post':
                    resp = self._session.post(_url, headers=_headers, data=_data, cookies=self._cookies if inherit_cookies else None)
                elif method.lower() == 'get':
                    resp = self._session.get(
                        _url + (f'?{"&".join([k + "=" + _data[k] for k in _data])}' if _data is not None else ''),
                        headers=_headers, cookies=self._cookies if inherit_cookies else None)
                if not inherit_cookies:
                    self._cookies = resp.cookies
                self.data = resp.content
                if mode == 't':
                    self.data = self.data.decode(_coding)
                return func(*args, **kwargs)
            inner_wrapper.__name__ = func.__name__
            return inner_wrapper

        return wrapper

    def decorator_flow(self, *handlers):
        def wrapper(func):
            def inner_wrapper(*args, **kwargs):
                self.data = self._handle(self.data, *handlers, **kwargs)
                return func(*args, **kwargs)
            inner_wrapper.__name__ = func.__name__
            return inner_wrapper

        return wrapper

    def _handle(self, data, *handlers, **kwargs):
        for handler in handlers:
            if type(handler) == list:
                result = []
                for single in handler:
                    result.append(self._handle(data, single))
                data = result
            elif type(handler) == dict:
                result = {}
                for key in handler:
                    single = handler[key]
                    result_key, = self._replace_all_params(kwargs, self._handle(data, key))
                    result[result_key] = self._handle(
                        data, single)
                data = result
            elif callable(handler):
                data = handler(data)
            else:
                return handler
        return data

    def _parse_template(self, template, kwargs, globals, locals):
        for match in re.findall(r'\<.*?\>', template):
            statement = match[1:-1]
            globals.update(kwargs)
            repl = eval(statement, globals, locals)
            template = template.replace(match, str(repl))
        return template

    def _replace_param(self, s, **kwargs):
        if type(s) == str:
            return self._parse_template(s, kwargs, globals(), locals())
        elif type(s) == list:
            result = []
            for item in s:
                result.append(self._replace_param(item, **kwargs))
            return result
        elif type(s) == dict:
            result = {}
            for key in s:
                result[self._replace_param(key, **kwargs)] = self._replace_param(s[key], **kwargs)
            return result

    def _replace_all_params(self, to_repl, *args):
        new_args = []
        for arg in args:
            new_args.append(self._replace_param(arg, **to_repl))
        return new_args

exec(register)

class _IoC(Candy):

    def __init__(self):
        self.beans = {}

    def decorator_component(self, clazz):
        def wrapper(*args, **kwargs):
            self.beans[clazz] = clazz()
        return wrapper
    
    def export_get_bean(self, clazz):
        return self.beans[clazz]

exec(register)