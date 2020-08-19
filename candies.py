from proto import *

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

    def decorator_catch_exception(self, Type, handler=None):
        def wrapper(func):
            def inner_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Type as e:
                    if handler is not None:
                        handler(e)
                    else:
                        traceback.print_exc()
            return inner_wrapper
        return wrapper

exec(register)

from concurrent.futures import ThreadPoolExecutor

class _Concurrent(Candy):

    def __init__(self):
        self.pool = ThreadPoolExecutor(max_workers=10)
        self.intervals = {}
    
    def export_set_max_workers(self, value):
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
    
    def decorator_immediate(self, *args, **kwargs):
        def wrapper(func):
            return func(*args, **kwargs)
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
