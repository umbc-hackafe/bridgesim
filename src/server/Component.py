from physics import Vector
from ClientAPI import expose, readable, writable, BaseContext

@readable('model', 'hp', 'mass', 'radius', 'position', 'orientation')
class Component:
    class Context(BaseContext):
        def __init__(self, instance=None, serial=None):
            if instance:
                self.universe = instance.ship.universe.id
                self.ship = instance.ship.id
                self.component = instance.id

            elif serial:
                _, self.universe, self.ship, self.component = serial

        def serialized(self):
            return ("Component", self.universe, self.ship, self.component)

        def instance(self, global_context):
            return global_context.universes[self.universe].entities[self.ship].components[self.component]

    def __init__(self, ship, config):
        self.ship = ship

        self.model = "ball"
        self.hp = 1
        self.mass = 1000
        self.radius = 1
        self.position = Vector()
        self.orientation = Vector(1, 0, 0)
        self.energy = 0.0
        self.idle = True

        self.__dict__.update(config)
        self.orientation = Vector(*self.orientation)
        self.position = Vector(*self.position)
        print(self.hp)

    def energyNeeded(self):
        if self.hp > 0:
            return .1
        else:
            return 0

    def takeDamage(self, amount):
        applied = min(self.hp, amount)
        self.hp -= applied
        return amount - applied

    def isDead(self):
        return self.hp == 0

    def tick(self, duration):
        return {}

class HullSection(Component):
    def __init__(self, ship, config):
        super().__init__(ship, config)

    def tick(self, duration):
        return super().tick(duration)

class CrewStation(Component):
    def __init__(self, ship, config):
        super().__init__(ship, config)

    def tick(self, duration):
        return super().tick(duration)

@writable('throttle', 'orientation')
class Drive(Component):
    def __init__(self, ship, config):
        self.throttle = 0.0
        self.thrustVector = Vector()
        super().__init__(ship, config)

    def energyNeeded(self):
        if self.hp > 0:
            return self.throttle
        else:
            return 0

    def tick(self, duration):
        self.thrustVector = self.orientation * self.energy * self.throttle * duration
        return super().tick(duration)

@readable('loadTime', 'loadStatus')
@writable('target')
class WeaponsStation(Component):
    def __init__(self, ship, config):
        super().__init__(ship, config)

        self.target = None
        self.payload = None
        self.loadTime = 0
        self.loadStatus = "Empty"

    @expose
    def load(self, payload):
        print("Loading")
        if self.weapons == "tube":
            if self.loadStatus == "Empty":
                self.loadStatus = "Loading"
                self.loadTime = payload.loadTime
                self.payload = payload

    @expose
    def unload(self, payload):
        if self.weapons == "tube":
            if self.loadStatus == "Loading":
                self.loadStatus = "Unloading"

    @expose
    def fire(self):
        print("Firing...")
        if self.weapons == "tube":
            print("check 1", self.loadStatus, self.hp, self.energy)
            if self.loadStatus == "Loaded" and self.hp > 0:
                print("check 2")
                self.payload.fire(self)
                self.loadStatus = "Empty"
                self.payload = None
        else:
          print("Damn...")
          pass
            # Fire the phasers here

    def energyNeeded(self):
        if self.weapons == "phaser" or self.loadStatus == "Loading" or self.loadStatus == "Unloading":
            return 1
        else:
            return .1

    def tick(self, duration):
#        print("Ticking tube", duration)
        if self.loadStatus == "Loading":
            self.loadTime -= self.energy
            if self.loadTime <= 0:
                print("Tube is loaded")
                self.loadStatus = "Loaded"
                print("LOADED")

        if self.loadStatus == "Unloading":
            self.loadTime += duration * self.energy
            if self.loadTime >= self.payload.loadTime:
                self.loadStatus = "Empty"
                self.payload = None

@readable('enabled')
class ShieldGenerator(Component):
    def __init__(self, ship, config):
        super().__init__(ship, config)

        self.baseRadius = self.radius
        self.enabled = False

    def takeDamage(self, amount):
        if self.enabled:
            applied = min(amount, self.shieldHp)
            self.shieldHp -= applied
            amount -= applied

        if self.shieldHp <= 0 or not self.enabled:
            applied = min(amount, self.hp)
            self.hp -= applied
            amount -= applied

        return amount

    @expose
    def enable(self):
        self.radius = self.shieldRadius
        self.enabled = True

    @expose
    def disable(self):
        self.radius = self.baseRadius
        self.enabled = False

    def energyNeeded(self):
        if self.enabled:
            return 1
        else:
            return .2

    def tick(self, duration):
        if self.hp > 0:
            self.shieldHp += self.shieldRecharge * duration * self.energy

COMPONENT_CLASSES = {
    "Component": Component,
    "HullSection": HullSection,
    "CrewStation": CrewStation,
    "Drive": Drive,
    "WeaponsStation": WeaponsStation,
    "ShieldGenerator": ShieldGenerator
}
def findComponent(name):
    if name in COMPONENT_CLASSES:
        return COMPONENT_CLASSES[name]
    else:
        return None
