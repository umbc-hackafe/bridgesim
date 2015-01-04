import sys
from Client import Client, ClientUpdater
from SocketNetworker import SocketNetworker
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

cherrypy.config.update( {
	'server.socket_port': 9000,
	'server.socket_host':'0.0.0.0',
})
WebSocketPlugin(cherrypy.engine).subscribe()
cherrypy.tools.websocket = WebSocketTool()

class Root():
    @cherrypy.expose
    def index(self):
        return 'some HTML with a websocket javascript connection'

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
            return list(obj.Context(instance=obj).serialized())
        return VectorEncoder.default(self, obj)

class ExpansionEncoder(ContextEncoder):
    def default(self, obj):
        if hasattr(obj, "__api_readable__"):
            return {k: getattr(obj, k) for k in obj.__api_readable__ if hasattr(obj, k)}
        return ContextEncoder.default(self, obj)

class ClientHandler(WebSocket):
    clients = {}
    def __init__(self, *args, **kwargs):
        self.failed = 0
        super().__init__(*args, **kwargs)
        self.listeners = []
        self.listening = False
        print("Client connected!")

        self.client = None

        if "clientid" in cherrypy.request.cookie:
            cookie_id = cherrypy.request.cookie["clientid"].value
            if cookie_id in ClientHandler.clients.keys():
                self.client = ClientHandler.clients[cookie_id]
                self.client.reinit(self)
                print("Reconnected cient {}".format(cookie_id))

        if not self.client:
            self.client = Client(self.api, None, self, self)
            self.client.id = str(uuid.uuid4())
            ClientHandler.clients[self.client.id] = self.client
            print("Connected new client {}".format(self.client.id))

        updater = ClientUpdater(self.universe, self.client)
        self.universe.updaters.append(updater)

    def opened(self):
        print("Test send")

    def send(self, data, expand=False):
        encoder=ContextEncoder
        if expand:
            encoder=ExpansionEncoder
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
            print(self.listeners)
            for i in self.listeners:
                print("Handling Message")
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
    def __init__(self, config, universe):
        self.__dict__.update(config)
        self.universe = universe
        self.store = self.universe.clientDataStore
        ClientHandler.universe = universe
        ClientHandler.store = self.universe.clientDataStore
        self.store = self.universe.clientDataStore
        self.clients = ClientHandler.clients

    def run(self):
            cherrypy.quickstart(Root(), '/', config={
				'/client': {
					'tools.websocket.on': True,
					'tools.websocket.handler_cls': ClientHandler
				},
				'/': {
					'tools.staticdir.on' : True,
				    'tools.staticdir.dir' : os.path.join( os.getcwd(), 'web/' ),
	    			'tools.staticdir.index' : 'index.html'
				}
			});

    def start(self, api):
        ClientHandler.api = api
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
