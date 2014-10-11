from ClientAPI import BaseContext, expose

class Lobby:
    class Context(BaseContext):
        def __init__(self, instance=None, context=None):
            pass

        def instance(self, global_context):
            return global_context.lobby

        def serialized(self):
            return ("Lobby",)

    def __init__(self, universes):
        self.universes = universes
        self.ships = {}

    @expose
    def createUniverse(self, properties):
        return id

    @expose
    def newShip(self, name, kind):
        return id

    @expose
    def joinShip(self, ship, components):
        pass

    @expose
    def materializeShip(self, ship, universe):
        pass
