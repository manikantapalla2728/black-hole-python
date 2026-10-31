"""Real execution tracing of the displayed source (sys.settrace).

Only code objects that live in physics.py are traced, so the
line numbers reported here are lines that REALLY executed.
"""
import os
import sys
import types


def _collect(code, out):
    out.add(code)
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            _collect(const, out)


class LineTracer:
    def __init__(self, module):
        self.path = os.path.abspath(module.__file__)
        self.targets = set()
        for obj in vars(module).values():
            self._scan(obj, module.__name__)
        self.events = []
        self.enabled = True

    def _scan(self, obj, modname):
        if isinstance(obj, (staticmethod, classmethod)):
            obj = obj.__func__
        if isinstance(obj, types.FunctionType):
            if obj.__module__ == modname:
                _collect(obj.__code__, self.targets)
        elif isinstance(obj, type) and obj.__module__ == modname:
            for attr in vars(obj).values():
                self._scan(attr, modname)

    def _global(self, frame, event, arg):
        if frame.f_code in self.targets:
            return self._local
        return None

    def _local(self, frame, event, arg):
        if event == "line":
            self.events.append(frame.f_lineno)
        return self._local

    def call(self, fn, *args, **kwargs):
        """Run fn with line tracing switched on for physics.py."""
        if not self.enabled:
            return fn(*args, **kwargs)
        prev = sys.gettrace()
        sys.settrace(self._global)
        try:
            return fn(*args, **kwargs)
        finally:
            sys.settrace(prev)

    def drain(self):
        events, self.events = self.events, []
        return events
