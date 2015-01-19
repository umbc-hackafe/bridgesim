import sys
from Client import Client, ClientUpdater
from SharedClientDataStore import SharedClientDataStore
import threading
import socket
import physics
import os
import json
import traceback
import uuid

import cherrypy
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
import jinja2

cherrypy.config.update( {
    'server.socket_port': 9000,
    'server.socket_host':'0.0.0.0',
    'engine.SIGTERM': False,
    'DEBUG': True
})
WebSocketPlugin(cherrypy.engine).subscribe()
cherrypy.tools.websocket = WebSocketTool()
env = jinja2.Environment(loader=jinja2.FileSystemLoader('../webgl/templates'))

class Root():
    # Because I'm lazy as hell...
    def url_for(self, dir, filename):
        return "/" + filename

    def template(self, name, **args):
        tmpl = env.get_template(name)
        return tmpl.render(config=cherrypy.config, url_for=self.url_for, **args)

    @cherrypy.expose
    def index(self):
        return self.template('index.html')

    @cherrypy.expose
    def lobby(self):
        return self.template('lobby.html')

    @cherrypy.expose
    def minimap(self):
        return self.template('minimap.html')

    @cherrypy.expose
    def weapons(self):
        return self.template('weapons.html')

    @cherrypy.expose
    def client(self):
        # you can access the class instance through
        handler = cherrypy.request.ws_handler

class VectorEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, physics.Vector):
            return list(obj.dimensions)
        return json.JSONEncoder.default(self, obj)

class ContextEncoder(VectorEncoder):
    def default(self, obj):
        if hasattr(obj, 'Context'):
            return {"context": list(obj.Context(instance=obj).serialized())}
        elif hasattr(obj, '__api_auto__'):
            return {"context": [type(obj).__name__]}
        return VectorEncoder.default(self, obj)

class ExpansionEncoder(ContextEncoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.done = False

    def default(self, obj):
        if self.done:
            return ContextEncoder.default(self, obj)
        if hasattr(obj, "__api_readable__"):
            self.done = True
            return {k: getattr(obj, k) for k in obj.__api_readable__ if hasattr(obj, k)}
        return ContextEncoder.default(self, obj)

class ClientHandler(WebSocket):
    clients = {}
    def __init__(self, *args, **kwargs):
        self.failed = 0
        super().__init__(*args, **kwargs)
        self.listeners = []
        self.listening = False
        self.open = False
        print("Client connected!")

        self.client = None

        if "clientid" in cherrypy.request.cookie:
            cookie_id = cherrypy.request.cookie["clientid"].value
            if cookie_id in ClientHandler.clients.keys():
                self.client = ClientHandler.clients[cookie_id]
                if self.client.sender and self.client.sender.open:
                    self.client.sender.close(1000, "Closing outdated connection")
                    print(self.client.sender.close)
                self.client.reinit(self.api, None, self, self)
                self.client.id = cookie_id
                print("Reconnected cient {}".format(cookie_id))

        if not self.client:
            self.client = Client(self.api, None, self, self)
            self.client.id = str(uuid.uuid4())
            ClientHandler.clients[self.client.id] = self.client
            print("Connected new client {}".format(self.client.id))

        updater = ClientUpdater(self.universe, self.client, self.api)
        self.universe.updaters.append(updater)


    def closed(self, code, message):
        self.open = False
        super().closed(code, message)
        self.client.destroy()

    def opened(self):
        self.open = True

    def send(self, data, expand=False):
        encoder=ContextEncoder
        if expand:
            data = ClientHandler.api.expand(data)
        try:
            encodeddata = json.dumps(data, cls=encoder, separators=(',',':')).encode('UTF-8')
            super().send(encodeddata)
        except Exception as e:
            print("Send Failed:")
            traceback.print_exc()
            self.failed += 1
            #print("Send Failed")
            if self.failed > 10:
                raise OSError("Error updating client "+str(self.client.id)+", destroying")

    def received_message(self, message):
        try:
            print(">>>", message.data)
            for i in self.listeners:
                msg = json.loads(message.data.decode('UTF-8'))
                if not 'context' in msg:
                    print("Adding context")
                    msg['context'] = [msg['op'].split("__")[0], self.client.id]
                i(msg)
        except Exception as e:
            traceback.print_exc()
            print("Receive Failed:")
            raise e
            #print("Receive Failed")
 
class NetworkServer:
    def __init__(self, config, universe=None):
        self.__dict__.update(config)
        self.universe = universe
        self.store = SharedClientDataStore(self)
        self.clients = ClientHandler.clients
        if universe:
            self.set_universe(universe)

    def set_universe(self, universe):
        self.universe = universe
        ClientHandler.universe = universe

    def stop(self):
        for client in self.clients.values():
            if not client.closed:
                client.sender.close(1001, "Server is shutting down.")
        cherrypy.engine.stop()

    def run(self):
        cherrypy.tree.mount(Root(), '/', config={
            '/client': {
                'tools.websocket.on': True,
                'tools.websocket.handler_cls': ClientHandler
            },
            '/': {
                'tools.staticdir.on' : True,
                'tools.staticdir.dir' : os.path.join( os.getcwd(), '../webgl/static/' ),
                'tools.staticdir.index' : 'index.html'
            }
        })
        cherrypy.engine.start()
        cherrypy.engine.block()

    def start(self, api):
        ClientHandler.api = api
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
