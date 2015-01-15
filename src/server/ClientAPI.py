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

def updates(*attrs):
    def decorator(func):
        print("{} may have been updated".format(",".join(attrs)))
        return func

    return decorator

def readable(*attrs):
    def decorator(cls):
        attr_set = set(attrs)
        print("Adding attrs {} to class {}".format(attrs, cls))
        if hasattr(cls, "__api_readable__"):
            attr_set |= set(cls.__api_readable__)

        setattr(cls, "__api_readable__", attr_set)

        return cls
    return decorator

def writable(*attrs):
    def decorator(cls):
        attr_set = set(attrs)
        if hasattr(cls, "__api_writable__"):
            attr_set |= set(cls.__api_writable__)

        setattr(cls, "__api_writable__", attr_set)

        return readable(*attrs)(cls)
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
        self.update_listeners = []
        self.instances = {}

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

    def resend_updates(self, listener):
        for kind, obj_set in list(self.instances.items()):
            for obj in set(obj_set):
                listener(kind, obj)

    def update_subscribe(self, listener):
        self.update_listeners.append(listener)
        self.resend_updates(listener)

    def update_unsubscribe(self, listener):
        if listener in self.update_listeners:
            self.update_listeners.remove(listener)

    def dispatch_update(self, kind, obj):
        if kind not in self.instances:
            self.instances[kind] = set()
        self.instances[kind].add(obj)

        for l in list(self.update_listeners):
            l(kind, obj)

    def resolve_contexts(self, obj, client=None):
        """
        Accepts an object and attempts to convert any serialized contexts
        it contains, of the form {"context": ["Type", 1, ...]}, into their
        corresponding instances.
        """

        if not obj:
            return obj

        if isinstance(obj, str):
            return obj

        try:
            if "context" in obj:
                return self.get(obj["context"], client=client)
        except TypeError:
            pass

        try:
            return {k: self.resolve_contexts(v, client) for k, v in obj.items()}
        except TypeError:
            pass
        except AttributeError:
            pass

        try:
            return [self.resolve_contexts(v, client) for v in list(obj)]
        except TypeError:
            pass

        return obj

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

    def find_base_class(self, cls):
        for base in cls.__bases__:
            if base == object or not hasattr(base, "__api_registered_base__"):
                return cls
            else:
                res = self.find_base_class(base)
                if res is not None:
                    return res
        return None

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

        cls.__api_registered_base__ = cls

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
            "writable": writable,
            "__old_setattr__": cls.__setattr__
        }

        if hasattr(cls, "__api_readable__") and not hasattr(cls, "__api_setattr_wrapped__"):
#            def closure(cls):
            setattr(cls, "__api_setattr_wrapped__", True)
            cls.__api_old_setattr = cls.__setattr__
            def new_setattr(s, name, value):
                # THIS NEEDS TO HAPPEN IN ANOTHER THREAD
                # Or at least somewhere that we won't block the sender...
                # maybe on the network thread
                if name != "__setattr__" and name in s.__api_readable__ and (not hasattr(s, name) or getattr(s, name) != value):
                    self.dispatch_update(cls.__name__, s)

                return self.classes[cls.__name__]["__old_setattr__"](s, name, value)
            cls.__setattr__ = new_setattr

        # Wrap the constructor so that we can keep track of it easier for fullsyncs
        if readable or writable:
            # We don't really care unless it has a readable_or_writable

            if self.find_base_class(cls) == cls:
                if not hasattr(cls, "__api_init_wrapped__"):
                    # Make sure we don't do it twice, which would be weird
                    setattr(cls, "__api_init_wrapped__", True)

                    # This closure is necessary; I'm not sure why, but I
                    # don't want to temp the python gods
                    def replace(cls):
                        old = cls.__init__

                        def new_init(s, *args, **kwargs):
                            # FIXME: This gets called twice for everything. Ha, good luck!
                            old(s, *args, **kwargs)

                            self.dispatch_update(s.__api_registered_base__.__name__, s)

                        cls.__init__ = new_init
                    replace(cls)
