event_funcs = {}

def evention(key):
    def decorator(func):
        event_funcs[key] = func
        return func
    return decorator