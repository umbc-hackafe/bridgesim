"""Contains functionality for exposing behavior to the client.

ClientAPI -- Main class for underlying implementation of the client
API.

BaseContext -- Base class for exposed classes using Context system.

GlobalContext -- Container class for global state available to
Contexts.

autocontext -- Class decorator for global or per-client classes.

expose -- Method decorator for exposing functions.

readable -- Class decorator for specifying API-readable attributes.

writable -- Class decorator for specifying API-writable attributes.

"""

class BaseContext:
    """Base class for implementing Context serialization and
    deserialization for a class.

    Methods -- serialized, instance

    This should be subclassed as a class attribute at the top level. e.g.:

    class Thingy:
        class Context(BaseContext):
            ...

    Also note that it *must* be called "Context" to be recognized by
    the API upon registration.

    """
    def __init__(self, instance=None, serial=None):
        """Initialize a Context.

        Keyword arguments:
        instance -- a full-fledged instance of the class (not its Context)
        serial   -- a serialized context, as defined by self.serialized()

        Only one of the arguments will ever be passed to the
        constructor at once. Whichever is passed, the constructor
        should extract the necessary information from it and generally
        save it.

        """
        pass

    def serialized(self):
        """Return a serialized representation of the Context as a tuple.

        Conventially, the first element in this tuple is the name of
        the class for which this Context is defined. The remaining
        elements are any necessary information (usually IDs) needed to
        retrieve the original instance from a GlobalContext. The
        result of this method is what will be passed as the "serial"
        argument to the constructor.

        """
        return ()

    def instance(self, global_context):
        """Return the instance of the parent class corresponding to this
        Context instance.

        Arguments:
        global_context -- A GlobalContext instance which may be used
        to locate the corresponding instance for this Context.

        """
        return None

class GlobalContext:
    """A container for global state which is needed by subclasses of
    BaseContext in order to locate their corresponding instances.

    Attributes:
    universes -- A list of all universes in the game.
    network   -- The NetworkServer instance.

    """
    def __init__(self, universes, network):
        self.universes = universes
        self.network = network

def autocontext(getter):
    """A class decorator which marks the class as having an instance which
    can be inferred just from the Client requesting it.

    Argument: A function which accepts the Client attempting to
    resolve an instance and a GlobalContext instance, and returns the
    corresponding instance.

    For example, the Client itself uses this decorator as such:

    @autocontext(lambda client, global_context: client)
    class Client:
        ...

    """
    def decorator(cls):
        if not hasattr(cls, "__api_auto__"):
            setattr(cls, "__api_auto__", getter)
        return cls
    return decorator

def expose(func=None, label=None, client=False):
    """A function decorator which exposes the target to the API.

    Arguments:
    func -- The function to be decorated

    Keyword arguments:
    label  -- The name under which to expose this function, if
              different from its real name.
    client -- If True, the function will receive a keyword argument
              "client" corresponding to the client which initiated
              the function call.

    """
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

def readable(*attrs):
    """A class decorator which exposes the given attributes of the target
    to the API in read-only mode.

    Arguments:
    *attrs -- Varargs, where each is the name of an attribute.

    """
    def decorator(cls):
        attr_set = set(attrs)
        print("Adding attrs {} to class {}".format(attrs, cls))
        if hasattr(cls, "__api_readable__"):
            attr_set |= set(cls.__api_readable__)

        setattr(cls, "__api_readable__", attr_set)

        return cls
    return decorator

def writable(*attrs):
    """A class decorator which exposes the given attributes of the target
    to the API in read-write mode.

    Arguments:
    *attrs -- Vararsg, where each is the name of an attribute.

    This decorator will implicitly apply @readable, so it is not
    necessary to do so manually.

    """
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
    """Class for handling registration of classes for exposure in the API,
    providing standard access methods for clients, and coordinating
    state updates for instances of registered classes.

    Attributes:
    classes   -- A dictionary for storing information for each class.
    instances -- A dictionary of {<type>: [ <instances>,] } for every
                 class registered with the API.

    Methods:
    onGet, onSet, onCall -- Resolve a context and perform an
                            operation on its instance.
    get                  -- Resolve a context to its instance.
    getTable             -- Return a dictionary of class names to
                            their methods and attributes.
    resend_updates       -- Resend all updates to a listener.
    update_[un]subscribe -- [Un]subscribe a listener for updates.
    resolve_contexts     -- Deserialize contexts in a primitive.
    expand               -- Expand a registered object into its
                            context and readable attributes.
    register             -- Register a class with the API.

    """
    def __init__(self, globalContext):
        """Initialize a ClientAPI object.

        Arguments:
        globalContext -- An instance of GlobalContext that will be used
                         for deserializing contexts.

        """
        self.classes = {}
        self.globalContext = globalContext
        self.update_listeners = []
        self.instances = {}

    def onGet(self, name, ctx, client=None):
        """Deserialize a class from a context and return one of its attributes
        in the form {"result": <value>}.

        Arguments:
        name -- The class name and attribute name, separated by a dot (e.g.,
                "SomeClass.some_attr").
        ctx  -- A serialized context for the instance whose attribute is to
                be retrieved.

        This method will raise an AttributeError if the named
        attribute has not been marked readable. If the attribute has
        been marked readable, but is not present in the resolved
        instance, {"result": None} will be returned.

        """
        cls, attr = name.split(".")
        classInfo = self.classes[cls]

        if attr not in classInfo["readable"]:
            raise AttributeError("Attribute {} is not readable -- did you @readable it?".format(attr))

        instance = self.get(ctx, cls, client)

        result = getattr(instance, attr, None)
        return {"result": result}

    def onSet(self, name, ctx, value, client=None):
        """Deserialize a class from a context and set one of its attributes,
        and return the new value in the form {"result": <value>}.

        Arguments:
        name  -- The class name and attribute name, separated by a dot (e.g.
                "SomeClass.some_attr").
        ctx   -- A serialized context for the instance whose attribute is to
                be set.
        value -- The new value for the specified attribute.

        This method will raise an AttributeError if the named
        attribute has not been marked writable.

        """
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
        """Deserialize a class from a context and call one of its methods, and
        return the result in the form {"result": <value>}.

        Arguments:
        name  -- The class name and attribute name, separated by a dot (e.g.
                "SomeClass.some_attr").
        ctx   -- A serialized context for the instance whose attribute is to
                be set.
        *args -- Varargs, to be directly passed to the specified function.

        Keyword arguments:
        **kwargs -- Keyword arguments, to be directly passed to the
                    specified function.

        This method will raise an AttributeError if the named method
        has not been exposed.

        """
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
        """Deserialize an arbitrary context.

        Arguments:
        ctx -- The context to deserialize.

        cls -- The name of the class to which the context will
               deserialize. If this is not given, it will be inferred
               from the context. It must be explicitly provided if the
               class uses the autocontext decorator.

        """
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
        """Return a dictionary with API-related information for each
        registered class.

        Example result:
        {
          "SomeClass": {
            "class": <class 'SomeClass'>,
            "context": <class 'SomeClass.Context'>,
            "methods": {
              "foo": {"callable" <function 'foo'>},
              "bar": {"callable": <function 'bar'>},
              "blah_client": {
                "callable": <function 'blah_client'>,
                "pass_client": True
              }
            },
            "readable": ["id", "kind", "name"],
            "writable": ["name"],
          },
          ...
        }

        """
        return self.classes

    def resend_updates(self, listener):
        """Send a listener all "base" updates, to ensure it has sufficiently
        up-to-date state.

        Arguments:
        listener -- A function to receive the updates, as described in
                    update_subscribe.

        """
        for kind, obj_set in list(self.instances.items()):
            for obj in set(obj_set):
                listener(kind, obj)

    def update_subscribe(self, listener):
        """Subscribe a listener function to all future state updates in all
        registered classes and send it the "base" updates.

        Arguments:
        listener -- A function to receive updates. It must accept two
                    arguments, where the first is the name of the
                    class of the updated object, and the second is the
                    object itself.

        """
        self.update_listeners.append(listener)
        self.resend_updates(listener)

    def update_unsubscribe(self, listener):
        """Unsubscribe a listener from all future state updates.

        """

        if listener in self.update_listeners:
            self.update_listeners.remove(listener)

    def dispatch_update(self, kind, obj):
        if kind not in self.instances:
            self.instances[kind] = set()
        self.instances[kind].add(obj)

        for l in list(self.update_listeners):
            l(kind, obj)

    def resolve_contexts(self, obj, client=None):
        """Accept an object and attempt to convert any serialized contexts it
        contains, of the form {"context": ["Type", 1, ...]}, into
        their corresponding instances.

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
        """Expand an object to expose its top-level attributes, leaving
        primitives as is and replacing objects with context with their
        serialized context (e.g., ["Entity",1,0)]).

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
        """Register a class with the API.

        This function performs a large number of modifications to the
        given class.  Most significantly, it will wrap the __setattr__
        and __init__ methods, in order to provide automatic detection
        of updates to its attributes.  Because of this, register must
        be called on a superclass before being called on any of its
        subclasses. This does not apply if the superclass has no API
        exposure and would not otherwise be registered, of course.

        """

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
