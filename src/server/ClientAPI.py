# This should be subclassed within each
# class that gets registered with the API
class BaseContext:
    def __init__(self, instance=None, serial=None):
        pass

    def serialized(self):
        return ()

    def instance(self, global_context):
        return None

# This is actually very different from a context.
# Meh. It just holds the things we need it to.
class GlobalContext:
    def __init__(self, universes, network):
        self.universes = universes
        self.network = network

# ** Function Decorator **
def expose(func, label=None):
    if not label:
        label = func.__name__
    setattr(func, "__api_exposed__", True)
    setattr(func, "__api_label__", label)
    return func

def readable(*attrs):
    def decorator(cls):
        if not hasattr(cls, "__api_readable__"):
            setattr(cls, "__api_readable__", [])
        cls.__api_readable__.extend([attr for attr in attrs if attr not in cls.__api_readable__])
        return cls
    return decorator

def writable(*attrs):
    def decorator(cls):
        if not hasattr(cls, "__api_readable__"):
            setattr(cls, "__api_readable__", [])

        if not hasattr(cls, "__api_writable__"):
            setattr(cls, "__api_writable__", [])

        cls.__api_readable__.extend(attrs)
        cls.__api_writable__.extend(attrs)
        return cls
    return decorator

# There are two parts to this:
#
# One is a decorator which, applied to a function,
# marks it as registerable through the Client API.
#
# The other is a method in the ClientAPI, which gets
# passed a Class Name and searches through it for any
# applicable classes, as well as a Context class. If
# the class does not have a context, then the call
# will fail.
#
# Also, each Context will have a constructor that
# accepts a global context and either its object, or
# a tuple which represents its serialized value. It
# should also have an 'object' method which returns
# the object to which the context refers. And finally
# there should be a 'serialized' method which returns
# a tuple that uniquely identifies the context within
# the global context.
class ClientAPI:
    def __init__(self, globalContext):
        self.classes = {}
        self.globalContext = globalContext

    def onGet(self, name, ctx):
        cls, attr = name.split(".")
        classInfo = self.classes[cls]

        if attr not in classInfo["readable"]:
            raise AttributeError("Attribute {} is not readable -- did you @readable it?".format(attr))

        context = classInfo["context"]
        instance = context(serial=ctx).instance(self.globalContext)

        result = getattr(instance, attr, None)
        return {"result": result}

    def onSet(self, name, ctx, value):
        cls, attr = name.split(".")
        classInfo = self.classes[cls]

        if attr not in classInfo["writable"]:
            raise AttributeError("Attribute {} is not writable -- did you @writable it?".format(attr))

        context = classInfo["context"]
        instance = context(serial=ctx).instance(self.globalContext)

        setattr(instance, attr, value)

        if attr in classInfo["readable"]:
            result = getattr(instance, attr)
        else:
            result = None

        return {"result": result}

    def onCall(self, name, ctx, *args, **kwargs):
        cls, func = name.split(".")
        classInfo = self.classes[cls]
        if func not in classInfo["methods"]:
            raise AttributeError("Method {} is not available -- did you @expose it?".format(func))

        context = classInfo["context"]
        instance = context(serial=ctx).instance(self.globalContext)

        method = classInfo["methods"][func]["callable"]
        result = method(instance, *args, **kwargs)

        return {"result": result}

    def getTable(self):
        return self.classes

    def register(self, cls):
        if not hasattr(cls, "Context"):
            raise AttributeError("Cannot register class {}; must have Context.".format(cls.__name__))
        if not issubclass(cls.Context, BaseContext):
            raise AttributeError("Cannot register class {}; Invalid Context.".format(cls.__name__))

        methods = {}
        for methname in dir(cls):
            method = getattr(cls, methname)
            if hasattr(method, "__api_exposed__") and hasattr(method, "__api_label__"):
                methods[method.__api_label__] = {"callable": method}

        readable = []
        writable = []
        if hasattr(cls, "__api_readable__"):
            for attrName in cls.__api_readable__:
                readable.append(attrName)

        if hasattr(cls, "__api_writable__"):
            for attrName in cls.__api_writable__:
                writable.append(attrName)

                if attrName not in readable:
                    readable.append(attrName)

        self.classes[cls.__name__] = {
            "class": cls,
            "context": cls.Context,
            "methods": methods,
            "readable": readable,
            "writable": writable
        }
