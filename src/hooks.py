

hooks = dict()

def add_hook(name, fn):
    name = name.lower()
    if name in hooks:
        hooks[name].append(fn)
    else:
        hooks[name] = [fn]


def run_hooks(name):
    name = name.lower()
    if name in hooks:
        for fn in hooks[name]:
            fn()
