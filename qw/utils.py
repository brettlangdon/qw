def dynamic_import(name):
    module, _, function = name.rpartition(".")
    mod = __import__(module, fromlist=[function])
    components = name.split(".")
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod
