#!/usr/bin/python
import Universe
import json
import Entity
import Ship
import Component
import time
import physics
import Missile
import WebsocketServer as NetworkServer
import os
import ClientAPI
import Client
import SharedClientDataStore
import sys
import AssetManager

frameRate = 100

assets = AssetManager.AssetManager(["../../assets/data/", "../data"])

shipConf = assets.find_asset("ships", "destroyer")
missileConf = assets.find_asset("weapons", "weapons")["weapons"]["nuke"]

size = width, height = 6400,4800

if "-v" in sys.argv:
  import pygame
  pygame.init()
  basicFont = pygame.font.SysFont(None, 24)
  SCALEFACTOR = 640/width
  screen = pygame.display.set_mode((int(width*SCALEFACTOR), int(height*SCALEFACTOR)))

universe = Universe.Universe(size)
universe.id = 0

network = NetworkServer.NetworkServer({}, universe)

api = ClientAPI.ClientAPI(ClientAPI.GlobalContext([universe], network))

# Register ALL the classes!
api.register(Universe.Universe)
api.register(Entity.Entity)
api.register(Ship.Ship)
api.register(Component.Component)
api.register(Component.Drive)
api.register(Component.WeaponsStation)
api.register(Component.ShieldGenerator)
api.register(SharedClientDataStore.SharedClientDataStore)
api.register(Client.ClientUpdater)
api.register(Client.Client)
api.register(Client.Player)

table = api.getTable()
print("==== Function Table ====")
for clsName, info in table.items():
  print()
  print("Class: {}".format(clsName))
  if not isinstance(info["context"], type):
    print("  Global: client.${}".format(clsName))

  if info["methods"]:
    print("=== Methods ===")
    for funcName in info["methods"]:
      print("  * {}()".format(funcName))
  if info["readable"]:
    print("=== Attributes ===")
    for attrName in info["readable"]:
      if "writable" in info and attrName in info["writable"]:
        print("  * {} (rw)".format(attrName))
      else:
        print("  * {} (r-)".format(attrName))

network.start(api)

ship1 = Ship.Ship(shipConf, universe)
ship1.name = "Aggressor"
ship2 = Ship.Ship(shipConf, universe)
ship2.name = "Victim"
ship3 = Ship.Ship(shipConf, universe)
ship3.name = "Cruiser"
ship1.location = physics.Vector(500,100,0)
ship1.velocity = physics.Vector(-7,-7,0)
ship2.location = physics.Vector(-400,1000,1000)
ship2.rotation = physics.Vector(0,0,0)
ship2.velocity = physics.Vector(5,-20,-50)
ship3.location = physics.Vector(-2500,1000,0)
ship3.rotation = physics.Vector(0,0,0)
ship3.velocity = physics.Vector(200,-20,5)
universe.add(ship1)
universe.add(ship2)
universe.add(ship3)

if "-v" in sys.argv:
  screen.fill((255,255,255))

universe.tick(5)
universe.collide()
universe.tock()

last = time.time()

running = True

while running:
  try:
    length = time.time()-last
    if "-f" in sys.argv:
      print("Frame rate: %.2f" % (1/length))
    data = universe.tick(length)
    #  data = universe.tick(.03)
    last = time.time()
    if "-v" in sys.argv:
      screen.fill((255,255,255))
      for i in data:
        pygame.draw.circle(screen, i[4], (int((i[0]-i[2])*SCALEFACTOR),int((i[1]-i[2])*SCALEFACTOR)), int(i[2]*SCALEFACTOR))
        text = basicFont.render(i[3], True, (0,0,0))
        textRect = text.get_rect()
        textRect.centerx = int((i[0]-i[2])*SCALEFACTOR)
        textRect.centery = int((i[1]-i[2])*SCALEFACTOR)-15
        screen.blit(text, textRect)
      pygame.display.flip()
    universe.collide()
    universe.tock()
    #  print("Sleeping:", time.time()-last)
    time.sleep(max((1/frameRate)-(time.time()-last),0))
  except KeyboardInterrupt:
    print("CLOSING")
    running = False
    network.stop()
