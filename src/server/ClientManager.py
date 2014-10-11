class ClientManager:
    def __init__(self, lobby):
        self.lobby = lobby
        self.clients = {}
        self.nextID = 1

    def register(self, client):
        client.id = nextID
        nextID += 1
        self.clients[client.id] = client
        # seq is an arbitrary anything so 
        client.sender.send({"seq": "registration",
                            "id": client.id,
                            "motd": "Welcome to Bridgesim"})


    def unregister(self, client):
        del self.clients[client.id]
        client.id = None
