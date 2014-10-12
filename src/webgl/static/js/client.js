function SocketWrapper(socket) {
    this.socket = socket;
    this.onOpens = [];
    this.onMessages = [];
    this.onErrors = [];
    this.onCloses = [];
    this.open = false;
    var wrap = this; // wat.

    socket.onopen = function(evt) {
	wrap.open = true;
	// APPARENTLY, this is now socket.this
	for (var l in wrap.onOpens.slice(0)) {
	    wrap.onOpens[l](evt);
	}
    }

    socket.onmessage = function(evt) {
	var jsonData = JSON.parse(evt.data);
	console.log("Receiving: ", jsonData);
	for (var l in wrap.onMessages.slice(0)) {
	    // Might need to do atob() here?
	    wrap.onMessages[l](jsonData);
	}
    }

    socket.onerror = function(evt) {
	for (var l in wrap.onErrors.slice(0)) {
	    wrap.onErrors[l](evt);
	}
    }

    socket.onclose = function(evt) {
	for (var l in wrap.onCloses.slice(0)) {
	    wrap.onCloses[l](evt);
	}
    }
}

SocketWrapper.prototype.addOnOpen = function(cb) {
    this.onOpens.push(cb);
}

SocketWrapper.prototype.addOnMessage = function(cb) {
    this.onMessages.push(cb);
}

SocketWrapper.prototype.addOnError = function(cb) {
    this.onErrors.push(cb);
}

SocketWrapper.prototype.addOnClose = function(cb) {
    this.onCloses.push(cb);
}

SocketWrapper.prototype.send = function(data) {
    if (this.open) {
	// FIXME maybe need btoa here?
	console.log("Sending: ", data);
	this.socket.send(JSON.stringify(data));
    } else {
	console.log("Socket not open. Queueing...");
	var theese = this;
	var func = function(){theese.socket.send(JSON.stringify(data));};
	// TODO auto-delete after calling?
	this.addOnOpen(func);
    }
}

SocketWrapper.prototype.close = function() {
    this.socket.close();
}

function RemoteFunction(socket, seq, name, callback, timeoutCallback) {
    this.socket = socket;
    this.seq = seq;
    this.name = name;
    this.timer = null;
    this.callback = callback;
    this.timeoutCallback = timeoutCallback;
    this.completed = false;
    this.boundMethod = null;
}

RemoteFunction.prototype.listener = function(data) {
    try {
	if (data && "seq" in data) {
	    if (data.seq == this.seq) {
		clearTimeout(this.timer);
		this.complete = true;
		this.callback(data);

		// if we leave this around we get exponential calls, oops
		var ourIndex = this.socket.onMessages.indexOf(this.boundMethod);
		delete this.socket.onMessages[ourIndex];
	    }
	}
    } catch (e) {
	console.log("Data is", data);
	console.log(e);
    }
};

RemoteFunction.prototype.call = function(context, kwargs) {
    if (!kwargs) kwargs = {};
    var data = {
	"seq": this.seq,
	"op": this.name,
	"args": Array.prototype.slice.call(arguments, 2),
	"kwargs": kwargs,
	"context": context
    };

    // javascript is stupid
    var theese = this;

    this.boundMethod = function(data){theese.listener(data);};
    this.socket.addOnMessage(this.boundMethod);

    this.socket.send(data);
    // All functions will have a 5 second timeout I guess
    if (this.callback) {
	this.timer = setTimeout(function() {theese.callback(null);}, 5000);
    } else {
	console.log("this.callback is not anything:");
	console.log(this.callback);
    }
}

window.client = {
    id: null, // This will be updated when connection is successful
    seq: 0,
    socket: null, // This needs to be set before we can initialize
    init: function(host, port, path) {
	if (this.socket) this.socket.close();
	this.socket = new SocketWrapper(new WebSocket("ws://" + host + ":" + port + (path[0] == "/" ? path : "/" + path)));
	this.socket.addOnOpen(function(evt) {
	    console.log("Socket opened. Now calling whoami...");
	    window.client.call("SharedClientDataStore__set", ["GlobalContext"], {callback: function(res) {
		this.id = res;
	    }, kwargs: {"key": "testVal", "value": "success"} });
	});
    },
    call: function(name, context, extras) {
	// Extras should be an object, e.g.:
	// client.call("SharedClientDataStore__get", ["SharedClientDataStore", 0],
	//           { args: ["test"],
	//             kwargs: {default: "unknown"},
	//             callback: function(data) {alert(data.result);}
	//           }
	// );
	var args = [], kwargs = {}, callback;
	console.log("Extras", extras);
	if (extras && 'args' in extras) args = extras.args;
	if (extras && 'kwargs' in extras) kwargs = extras.kwargs;
	if (extras && 'callback' in extras) {
	    callback = extras.callback;
	    console.log("callback", callback);
	}
	var tmpSeq = ++this.seq;
	var rf = new RemoteFunction(this.socket, tmpSeq, name, callback, null);
	var newArgs = [context, kwargs].concat(args);
	rf.call.apply(rf, newArgs);
    }
}
