import uuid
import random
import traceback
from ClientAPI import expose, readable, autocontext

ALL_KINDS = (
    "entity",
    "comms",
    "weapons",
    "engineer",
    "helm",
    "ship",
    "meta",
    "universe",
    "store"
)

class ClientClosedException(Exception):
    pass

class Client:
    def __init__(self, api, address, server, sender):
        self.updates = {}
        self.sender = sender
        self.address = address
        self.server = server
        self.api = api
        self.maxage = 30
        self.sender.listeners.append(self.dataReceived)
        self.specials = {"whoami": (lambda d: self.id),
                         "universes": (lambda d: [self.server.universe]),
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

    def reinit(self, sender):
        self.updates = {}
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
                        
                        # handle method calls
                        if funcName in info["methods"]:
                            result = self.api.onCall(clsName + "." + funcName,
                                                     context, *args, client=self, **kwargs)

                        # handle setting properties
                        elif funcName in info["writable"] and len(data["args"]) == 1:
                            result = self.api.onSet(clsName + "." + funcName,
                                                    context, *args)
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
        if kind not in self.updates:
            self.updates[kind] = []

        if kind == "entity":
            self.updates[kind].extend(data)
        if kind == "store":
            self.updates[kind].extend(data)
        # TODO add the remaining kinds of updates

    def destroy(self):
        self.closed = True
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

    @expose
    def fullSync(self):
        self.sendUpdates(ALL_KINDS)

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

    def sendUpdates(self, kinds):
        for kind in kinds:
            if kind == "entity":
                for universe in self.universes:
                    for entity in universe.entities.values():
                        self.client.queueUpdate(kind, self.client.api.expand(entity))
            elif kind == "comms":
                pass
            elif kind == "weapons":
                pass
            elif kind == "engineer":
                pass
            elif kind == "helm":
                pass
            elif kind == "ship":
                pass
            elif kind == "meta":
                pass
            elif kind == "universe":
                pass
            elif kind == "store":
                for update in self.client.server.store.get_updates(self.client):
                    if update:
                        self.client.queueUpdate(kind, update)
                self.client.server.store.dequeue_update(None, self.client)

        if self.api.hasUpdates:
            for cls, members in self.api.getUpdates().items():
                for m in members:
                    self.client.queueUpdate(cls, self.api.expand(m))

        try:
            if self.client.updates:
                self.client.sendUpdate()
        except ClientClosedException:
            print("Canceling updates; client closed")
            self.clientWants = {}
            self.offsets = {}

    def tick(self):
        toUpdate = []
        for kind in self.clientWants:
            if self.clientWants[kind] > 0 and self.ticks % self.clientWants[kind] == self.offsets[kind]:
                toUpdate.append(kind)

        self.sendUpdates(toUpdate)

        self.ticks += 1
