import uuid
import random
import traceback
from ClientAPI import BaseContext, expose, readable, writable, autocontext

class ClientClosedException(Exception):
    pass

@autocontext(lambda c, g: c)
@readable('player')
class Client:
    def __init__(self, api, address, server, sender):
        self.updates = {}
        self.sender = sender
        self.address = address
        self.server = server
        self.api = api
        self.player = Player(self, self.api)
        self.maxage = 30
        self.sender.listeners.append(self.dataReceived)
        self.specials = {"whoami": (lambda d: self.id),
                         "universes": (lambda d: [self.server.universe]),
                         "players": (lambda d: [client.player for client
                             in self.server.clients.values() if
                             client.sender.open]),
                         "expand": (lambda d: self.api.get(list(d["context"]))),
                         "functions": lambda d: {cls:
                                                 {"readable": info["readable"],
                                                  "writable": info["writable"],
                                                  "methods": [m for m in info["methods"]],
                                                  "context": isinstance(info["context"], type)}
                                                 for cls, info in self.api.getTable().items()},
                         "specials": lambda d: list(self.specials.keys()),
                     }
        self.closed = False

    def reinit(self, api, address, server, sender):
        self.api = api
        self.address = address
        self.server = server
        self.sender = sender

        self.sender.listeners.append(self.dataReceived)
        self.closed = False

    def dataReceived(self, data):
        if self.closed:
            raise ClientClosedException()
        if data and "op" in data:
            if "seq" in data:
                try:
                    if data["op"] in self.specials:
                        result = {"result": self.specials[data["op"]](data)}
                    else:
                        clsName, funcName = data["op"].split('__', 2)
                        if clsName not in self.api.classes:
                            raise Exception("Could not find {} in API".format(clsName))

                        info = self.api.classes[clsName]
                        context = data.get("context", ())
                        args = data.get("args", [])
                        kwargs = data.get("kwargs", {})

                        args = self.api.resolve_contexts(args, client=self)
                        kwargs = self.api.resolve_contexts(kwargs, client=self)

                        # handle method calls
                        if funcName in info["methods"]:
                            result = self.api.onCall(clsName + "." + funcName,
                                                     context, *args, client=self, **kwargs)

                        # handle setting properties
                        elif funcName in info["writable"] and len(data["args"]) == 1:
                            result = self.api.onSet(clsName + "." + funcName,
                                                    context, *args, client=self)
                            print("Client set {} to {} in class {}".format(
                                funcName, data["args"][0], clsName))

                        # handle getting properties
                        elif funcName in info["readable"] and len(data["args"]) == 0:
                            result = self.api.onGet(clsName + "." + funcName,
                                                    context, *args, client=self, **kwargs)
                            print("Client got {} of class {}".format(funcName, clsName))
                        # unavailable function?
                        else:
                            print("Client tried to do {}.{}. Returning error.".format(funcName, clsName))
                            raise Exception("Operation not found")

                    rDict = {"result": None, "seq": data["seq"]}
                    rDict.update(result)
                    self.sender.send(rDict, expand=(data["op"] == "expand" or "expand" in data and data["expand"]))
                except ValueError:
                    print("Warning: received invalid op", data["op"])
                except Exception as e:
                    print("Exception while sending response:")
                    print(e)
                    traceback.print_exc()
                    self.sender.send({"result": None, "error": str(e), "seq": data["seq"]})
            else:
                print("Warning: received command without seq")
        else:
            print("Warning: received invalid op", data["op"])

    def queueUpdate(self, kind, *data):
        if self.closed:
            raise ClientClosedException()
        if data and kind not in self.updates:
            self.updates[kind] = []

        self.updates[kind].extend(data)

    def destroy(self):
        self.closed = True
        self.sender.listeners.remove(self.dataReceived)
        self.sender.close()

    def sendUpdate(self):
        if self.closed:
            raise ClientClosedException()
        if self.updates:
            self.updates['updates'] = True
            self.sender.send(self.updates)
        self.updates = {}

@readable('universes')
@autocontext(lambda c,g:c.updater)
class ClientUpdater:
    def __init__(self, universe, client, api):
        self.universes = [universe]
        self.client = client
        self.client.updater = self
        self.api = api

        self.ticks = 0

        # {"kind": <frequency>}
        self.clientWants = {}
        # {"kind": <offset>}
        self.offsets = {}
        # {"kind": <set>}
        self.updates = {}

        self.api.update_subscribe(self.onUpdate)

    @expose
    def fullSync(self):
        self.api.resend_updates(self.onUpdate)
        self.sendUpdates(["*"])

    @expose
    def stopUpdates(self, kind):
        self.clientWants[kind] = 0

    @expose
    def requestUpdates(self, kind, frequency):
        self.clientWants[kind] = frequency
        if kind not in self.offsets:
            # We use a random offset to attempt a more
            # steady usage of networking
            self.offsets[kind] = random.randrange(frequency)

        if kind not in self.updates:
            self.updates[kind] = set()

    def onUpdate(self, kind, obj):
        if kind not in self.updates:
            self.updates[kind] = set()
        self.updates[kind].add(obj)

    def sendUpdates(self, kinds):
        if kinds == ["*"]:
            for kind, update in list(self.updates.items()):
                self.client.queueUpdate(kind, *[self.client.api.expand(obj) for obj in update])
                del self.updates[kind]
        else:
            for kind in kinds:
                if kind in self.updates and self.updates[kind]:
                    self.client.queueUpdate(kind, *[self.client.api.expand(obj) for obj in self.updates[kind]])
                    del self.updates[kind]

        try:
            if self.client.updates:
                self.client.sendUpdate()
        except ClientClosedException:
            pass

    def tick(self):
        try:
            toUpdate = []
            for kind in self.clientWants:
                if self.clientWants[kind] > 0 and self.ticks % self.clientWants[kind] == self.offsets[kind]:
                    toUpdate.append(kind)

            self.sendUpdates(toUpdate)

            self.ticks += 1

        except ClientClosedException:
            pass

@writable('universe', 'name', 'ship', 'component')
class Player:
    class Context(BaseContext):
        def __init__(self, instance=None, serial=None):
            if instance:
                self.id = instance.client.id

            elif serial:
                _, self.id = serial

        def serialized(self):
            return ("Player", self.id)

        def instance(self, global_context):
            return global_context.network.clients[self.id].player

    def __init__(self, client, api):
        self.universe = None
        self.client = client
        self.api = api
        self.name = ""
        self.ship = None
        self.component = None
