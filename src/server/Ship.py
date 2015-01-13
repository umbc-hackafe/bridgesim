from Entity import Entity
from Component import *
from Missile import Missile
from ClientAPI import writable

@writable('name')
class Ship(Entity):
  class Context(Entity.Context):
    def serialized(self):
      return ("Ship", self.universe, self.id)

  def __init__(self, config, universe):
    super().__init__(config, universe)
    self.__dict__.update(config)
    self.energy = self.maxEnergy

    # How much power Engineering is giving to each component - [0, 1] normally
    self.energySupply = {}

    self.numComponents = 0

    temp = {}
    for i in self.components:
      comp = findComponent(i['type'])(self, i)
      comp.id = self.numComponents
      self.numComponents += 1
      temp[comp.id] = comp
      self.energySupply[comp] = 1
    self.components = temp
    self.name = "Ship"
    
  def collide(self, other):
#    print("I got hit!")
    if type(other) is Missile:
      self.takeDamage(other.getDamage())
      
  def getID(self):
    return self.name

  def takeDamage(self, damage):
    print("I'm hit!", damage)
    for i in self.components.values():
      print(i.type, "Took damage")
      damage = i.takeDamage(damage)
      if damage <= 0:
        break
      
  def tick(self, duration):
    # Figure out how much each component wants and is being allowed
    needed = {component: component.energyNeeded() * duration * self.energySupply[component] for component in self.components.values()}
    totalNeeded = sum(needed.values())
    factor = 1 if totalNeeded <= self.energy else self.energy / totalNeeded

    # do this before looping so nothing grabs power allotted to something else
    self.energy -= totalNeeded * factor

    for i in self.components.values():
      i.energy = factor * duration * self.energySupply[i] * needed[i]
      i.tick(duration)
      if type(i) == Drive:
        self.thrustVectors[i.id] = (i.orientation, i.position, i.thrustVector)
    return super().tick(duration)
  
  def tock(self):
    for i in self.components.values():
      if not i.isDead():
        return
    print("Boom!")
    self.destroy()
