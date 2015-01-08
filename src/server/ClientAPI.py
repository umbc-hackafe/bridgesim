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

def autocontext(getter):
    def decorator(cls):
        if not hasattr(cls, "__api_auto__"):
            setattr(cls, "__api_auto__", getter)
        return cls
    return decorator

# ** Function Decorator **
def expose(func=None, label=None, client=False):
    if func != None:
        print("expose({}, label={}, client={})".format(func, label, client))
        if not label:
            label = func.__name__
        setattr(func, "__api_exposed__", True)
        setattr(func, "__api_label__", label)
        if client:
            setattr(func, "__api_pass_client__", True)
        return func
    else:
        def partial(func):
            return expose(func, label=label, client=client)
        return partial

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

    def onGet(self, name, ctx, client=None):
        cls, attr = name.split(".")
        classInfo = self.classes[cls]

        if attr not in classInfo["readable"]:
            raise AttributeError("Attribute {} is not readable -- did you @readable it?".format(attr))

        instance = self.get(ctx, cls, client)

        result = getattr(instance, attr, None)
        return {"result": result}

    def onSet(self, name, ctx, value, client=None):
        cls, attr = name.split(".")
        classInfo = self.classes[cls]

        if attr not in classInfo["writable"]:
            raise AttributeError("Attribute {} is not writable -- did you @writable it?".format(attr))

        instance = self.get(ctx, cls, client)

        setattr(instance, attr, value)

        if attr in classInfo["readable"]:
            result = getattr(instance, attr)
        else:
            result = None

        return {"result": result}

    def onCall(self, name, ctx, *args, client=None, **kwargs):
        cls, func = name.split(".")
        classInfo = self.classes[cls]
        if func not in classInfo["methods"]:
            raise AttributeError("Method {} is not available -- did you @expose it?".format(func))

        instance = self.get(ctx, cls, client)

        method = classInfo["methods"][func]["callable"]
        if classInfo["methods"][func]["pass_client"]:
            kwargs["client"] = client
        result = method(instance, *args, **kwargs)

        return {"result": result}

    def get(self, ctx, cls=None, client=None):
        if not cls:
            cls = ctx[0]
        classInfo = self.classes[cls]

        context = classInfo["context"]
        if isinstance(context, type):
            instance = context(serial=ctx).instance(self.globalContext)
        else:
            instance = context(client, self.globalContext)

        return instance

    def getTable(self):
        return self.classes

    def expand(self, obj):
        """
        Expands an object to expose all its top-level attributes, leaving
        primitives as is and turning Context-having objects into their
        context's primitive (e.g., ["Entity",1,0)]). This prevents
        having recursive objects.
        """

        if hasattr(obj, "__api_readable__"):
            result = {
                k: getattr(obj, k) for k in obj.__api_readable__
                }
            if hasattr(obj, "Context"):
                result.update({"context": obj.Context(instance=obj).serialized()})
        else:
            result = obj
        return result

    def register(self, cls):
        if hasattr(cls, "__api_auto__"):
            context = cls.__api_auto__
        else:
            if not hasattr(cls, "Context"):
                raise AttributeError("Cannot register class {}; must have Context or @autocontext.".format(cls.__name__))
            if not issubclass(cls.Context, BaseContext):
                raise AttributeError("Cannot register class {}; Invalid Context.".format(cls.__name__))
            context = cls.Context

        methods = {}
        for methname in dir(cls):
            method = getattr(cls, methname)
            if hasattr(method, "__api_exposed__") and hasattr(method, "__api_label__"):
                methods[method.__api_label__] = {"callable": method}
                if hasattr(method, "__api_pass_client__") and method.__api_pass_client__:
                    methods[method.__api_label__]["pass_client"] = True
                else:
                    methods[method.__api_label__]["pass_client"] = False

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
            "context": context,
            "methods": methods,
            "readable": readable,
            "writable": writable
        }
