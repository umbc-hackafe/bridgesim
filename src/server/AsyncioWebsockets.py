import asyncio
import threading
import websockets

@asyncio.coroutine
def client_input(websocket, path, client):
    while True:
        data = yield from websocket.recv()
        if data is None:
            break
        # handle client commands here
        #
        # data will be string or bytes depending on whether you pased a binary blob or a
        # string in the JS
        
@asyncio.coroutine
def tick_output(websocket, path, client):
    while True:
        # wait on an asyncio.event here for the update to happen. Make sure to yield to
        # the event, otherwise, it will just lock here.
        
        # generate the update data to send here

        if not websocket.open:
            break

        # send the message here.
        yield from websocket.send('')

@asyncio.coroutine
def websocket_handler(websocket, path):
    # create or get a client object here an give it an asyncio.event to wait on in
    # updates. Set these events so they get set by the physics tick, or some other
    # periodic function. Make sure updates to client change data are thread safe.
    client = None

    # you can read the initial message from the client here and send a response.

    tasks = [
        asyncio.async(client_input(websocket, path, client)),
        asyncio.async(tick_output(websocket, path, client)),
    ]

    yield from asyncio.wait(tasks)

def threaded_event_loop(loop, host, port):
    asyncio.set_event_loop(loop)
    start_server = websockets.serve(websocket_handler, host, port)
    loop.run_until_complete(start_server)
    loop.run_forever()


def start_threaded(host='localhost', port=8010):
    loop = asyncio.get_event_loop()
    thread = threading.Thread(target=threaded_event_loop, args=(loop, host, port))
    thread.start()
