import json
import math
import physics
import random
import time
from ClientAPI import BaseContext, readable

@readable('location', 'rotation', 'velocity', 'universe', 'radius', 'mass', 'events', 'id')
class Entity:
  class Context(BaseContext):
    def __init__(self, instance=None, serial=None):
      if instance:
        self.universe = instance.universe.id
        self.id = instance.id

      elif serial:
        _, self.universe, self.id = serial

    def serialized(self):
      return ("Entity", self.universe, self.id)

    def instance(self, global_context):
      return global_context.universes[self.universe].entities[self.id]

  class Event():
    def __init__(self):
      self.start = time.time()
      self.type = "Generic"

    def age(self):
      return time.time() - self.start

    def __str__(self):
      return json.dumps({"type":self.type,
        "age": self.age()})
  def __init__(self, config, universe, radius=100, mass=1000):
    self.thrustVectors = {}
    self.location = physics.Vector(0,0,0)
    self.rotation = physics.Vector(0,0,0,1)
    self.velocity = physics.Vector(0,0,0)
    self.universe = universe
    self.radius = radius
    self.mass = mass
    self.color = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
    self.events = []
  
  def getID(self):
    return self.id

  def instantiate(self):
    self.universe.add(self)
    
  def destroy(self):
    self.universe.remove(self)
    
  def checkCollide(self, other):
    vector = self.location - other.location
    distance = vector.magnitude()
    if distance < self.radius + other.radius:
      return True
    return False
  
  def tick(self, duration):
    self.location += self.velocity*duration
    return self.location[0], self.location[1], self.radius, self.getID(), self.color

  def tock(self):
    return

