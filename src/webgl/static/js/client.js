function SocketWrapper(socket) {
    this.socket = socket;
    this.queuedData = [];
    this.onOpens = [];
    this.onMessages = [];
    this.onErrors = [];
    this.onCloses = [];
    this.open = false;
    var wrap = this; // wat.

    socket.onopen = function(evt) {
        // Log the socket opening.
        console.log("WebSocket opened!")

	    wrap.open = true;
	    // APPARENTLY, this is now socket.this
	    for (var l in wrap.onOpens.slice(0)) {
	        wrap.onOpens[l](evt);
	    }

	    for (var d in wrap.queuedData) {
	        wrap.send(wrap.queuedData[d]);
	    }
	    wrap.queuedData = [];
    }

    socket.onmessage = function(evt) {
	    var jsonData = JSON.parse(evt.data);
	    console.log("Receiving: ", jsonData);
	    if (jsonData == null) {
	        console.log("Data is null... that's weird.");
	    } else {
	        for (var l in wrap.onMessages.slice(0)) {
		        // Might need to do atob() here?
		        wrap.onMessages[l](jsonData);
	        }
	    }
    }

    socket.onerror = function(evt) {
	    for (var l in wrap.onErrors.slice(0)) {
	        wrap.onErrors[l](evt);
	    }
    }

    socket.onclose = function(evt) {
        // Log the closing
        console.log("WebSocket closed!");

	    for (var l in wrap.onCloses.slice(0)) {
	        wrap.onCloses[l](evt);
	    }
    }
}

SocketWrapper.prototype.addOnOpen = function(cb) {
    if (this.open) {
        cb();
    }
    this.onOpens.push(cb);
}

SocketWrapper.prototype.addOnMessage = function(cb) {
    this.onMessages.push(cb);
}

SocketWrapper.prototype.addOnError = function(cb) {
    this.onErrors.push(cb);
}

SocketWrapper.prototype.addOnClose = function(cb) {
    if (!this.open) {
        cb();
    }
    this.onCloses.push(cb);
}

SocketWrapper.prototype.send = function(data) {
    if (this.open) {
	// FIXME maybe need btoa here?
	console.log("Sending: ", data);
	this.socket.send(JSON.stringify(data));
    } else {
	console.log("Socket not open. Queueing seq#" + data.seq);
	// TODO auto-delete after calling?
	this.queuedData.push(data);
    }
}

SocketWrapper.prototype.close = function() {
    this.socket.close();
}

function RemoteFunction(socket, seq, name, callback, timeoutCallback, expand) {
    this.socket = socket;
    this.seq = seq;
    this.name = name;
    this.timer = null;
    this.callback = callback;
    this.timeoutCallback = timeoutCallback;
    this.completed = false;
    this.boundMethod = null;
    this.expand = expand;
}

RemoteFunction.prototype.listener = function(data) {
    try {
	if (data && "seq" in data) {
	    if (data.seq == this.seq) {
		clearTimeout(this.timer);
		this.complete = true;
		if (this.callback)
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
	"context": context,
	"expand": this.expand
    };

    // javascript is stupid
    var theese = this;

    this.boundMethod = function(data){theese.listener(data);};
    this.socket.addOnMessage(this.boundMethod);

    this.socket.send(data);
    // All functions will have a 5 second timeout I guess
    var rf = this;
    if (this.callback) {
	this.timer = setTimeout(function() {
	    console.log("Call (seq#" + theese.seq + ") timed out.");
	    if (rf.timeoutCallback) {
		rf.timeoutCallback();
	    }
	}, 5000);
    } else {
	console.log("this.callback is not anything:");
	console.log(this.callback);
    }
}

function Client(host, port, path, doneCB) {
    this.id = null; // This will be updated when connection is successful
    this.socket = null;
    this.seq = Math.floor(Math.random() * 9007199254740992);
    this.doneCB = doneCB;
    this.init(host, port, path);
}

Client.prototype.init = function(host, port, path) {
    if (this.socket) this.socket.close();
    this.socket = new SocketWrapper(new WebSocket("ws://" + host + ":" + port + (path[0] == "/" ? path : "/" + path)));
    var client = this;
    this.socket.addOnOpen(function() {
	client.call("functions", null, {
	    callback: function(data) {
		client.loadFunctions(data.result);
		client.call("specials", null, {
		    callback: function(data) {
			client.loadSpecials(data.result);
			client.call("whoami", null, {
			    callback: function(data) {
				client.id = data.result;
				if (client.doneCB) client.doneCB();
			    }
			});
		    }
		});
	    }
	});
    });
};

Client.prototype.proxyContexts = function(obj) {
    var type = typeof obj;
    if (obj == null || type != "object") {
	return obj;
    }

    var created = JSON.parse(JSON.stringify(obj));
    for (var k in created) {
	if (k == "context" && created.context != null) {
	    return new this.proxyClasses[created.context[0]](created.context);
	} else {
	    created[k] = this.proxyContexts(created[k]);
	}
    }
    return created;
};

Client.prototype.loadSpecials = function(list) {
    var client = this;
    client["$Specials"] = {};
    for (var k in list) {
	var fName = list[k];
	var f = function(fName) {
	    client.$Specials[fName] = function() {
		var proxy = this;
		var args = [].slice.call(arguments);
		var len = args.length;
		var kwargs = {};
		if (len > 0) {
		    if (typeof args[len-1] === 'object') {
			kwargs = args[len-1];
			len--;
			args = args.slice(0,-1);
		    }
		}

		return new Promise(function(resolve, reject) {
		    client.call(fName, null, {
			args: args,
			kwargs: kwargs,
			callback: function(data) {
			    resolve(client.proxyContexts(data.result));
			},
			timeout: function() {
			    reject(Error("Call timed out"));
			}
		    });
		});
	    };
	};
	f(fName);
    }
};

Client.prototype.loadFunctions = function(map) {
    var client = this;
    this.cache = new ObjectCache(this, this.socket);
    this.proxyClasses = {};

    for (var className in map) {
	var readable = map[className]["readable"];
	var writable = map[className]["writable"];
	var methods = map[className]["methods"];
	var isGlobal = !map[className]["context"];

	this.cache.registerClass(className, readable, writable);

	var fffffffuuuuuuuuuuuu = function(className, readable, writable) {
	    client.proxyClasses[className] = function(ctx) {
		this.context = ctx;
		var proxy = this;

		for (var i in readable) {
		    var attr = readable[i];
		    var isWritable = writable.indexOf(attr) >= 0;
		    Object.defineProperty(this, attr, {
			get: function() {
			    var res = client.cache.get(this.context, className, attr);
			    return res;
			},
			set: function(val) {
			    return isWritable ? proxy["__set_" + attr](val) : Error(attr + " is not writable");
			}
		    });
		}
	    };
	};
	// I assure you this name is quite appropriate
	fffffffuuuuuuuuuuuu(className, readable, writable);

	var types = {};
	for (var i in methods) {
	    types[methods[i]] = "method";
	}

	for (var i in writable) {
	    types[writable[i]] = "writable";
	}
	var methodsAndWritable = methods.concat(writable);

	for (var i in methodsAndWritable) {
	    var prop;
	    if (types[methodsAndWritable[i]] == "writable") {
		prop = "__set_" + methodsAndWritable[i];
	    } else {
		prop = methodsAndWritable[i];
	    }

	    // Did I mention...
	    var f = function(clsName, pName) {
		client.proxyClasses[clsName].prototype[pName] =
		    function() {
			var proxy = this;
			var args = [].slice.call(arguments);
			var len = args.length;
			var kwargs = {};
			if (len > 0) {
			    if (typeof args[len-1] === 'object') {
				kwargs = args[len-1];
				len--;
				args = args.slice(0,-1);
			    }
			}

			return new Promise(function(resolve, reject) {
			    client.call(clsName + "__" + pName,
					proxy.context,
					{
					    args: args,
					    kwargs: kwargs,
					    callback: function(data) {
						resolve(client.proxyContexts(data.result));
					    },
					    timeout: function() {
						reject(Error("Call timed out"));
					    }
					}
				       );
			});
		    };
	    };

	    // ... how much I hate Javascript?
	    f(className, prop);
	}

	if (isGlobal) {
	    client['$' + className] =  new client.proxyClasses[className](null);
	}
    }
}

Client.prototype.call = function(name, context, extras) {
    // Extras should be an object, e.g.:
    // client.call("SharedClientDataStore__get", ["SharedClientDataStore", 0],
    //           { args: ["test"],
    //             kwargs: {default: "unknown"},
    //             callback: function(data) {alert(data.result);}
    //           }
    // );
    var args = [], kwargs = {}, callback, timeout = null;
    var expand = false;
    if (extras && 'args' in extras) args = extras.args;
    if (extras && 'kwargs' in extras) kwargs = extras.kwargs;
    if (extras && 'callback' in extras) callback = extras.callback;
    if (extras && 'expand' in extras) expand = extras['expand'];
    if (extras && 'timeout' in extras) timeout = extras['timeout'];

    this.seq += 1;
    var tmpSeq = this.seq;
    var rf = new RemoteFunction(this.socket, tmpSeq, name, callback, timeout, expand);
    var newArgs = [context, kwargs].concat(args);
    rf.call.apply(rf, newArgs);
};

Client.prototype.quit = function() {
    console.log("Quitting");
    this.socket.close();
}

function hashContext(context) {
    if (context) {
	return {bucket: context[0],
		key: context.slice(1).join(".")};
    } else {
	return 0;
    }
}

function ObjectCache(client, socket) {
    this.client = client;
    this.socket = socket;

    this.states = {};

    // I have to do this
    // because
    // if I don't
    // handleUpdates gets a 'this'
    // which is... a sparse array?
    // with [0: some random function]
    // and sometimes [4: some random function]
    // depending on when it gets called
    // because
    // like
    // that makes sense
    // right?
    var that = this;
    socket.addOnMessage(function(data) {that.handleUpdates(data);});
}

ObjectCache.prototype.get = function(context, cls, attr) {
    var hash = hashContext(context);
    var that = this;

    if (hash == 0) {
	hash = {bucket: cls, key: 0};
    }

    if (hash.bucket in this.states) {
	if ((hash.key + "." + attr) in this.states[hash.bucket]) {
	    return new Promise(function(resolve) {
		resolve(that.client.proxyContexts(that.states[hash.bucket][hash.key + "." + attr]));
	    });
	}
    }

    return new Promise(function(resolve) {
	that.client.call(cls + "__" + attr, context, {
	    callback: function(data) {
		that.states[hash.bucket][hash.key + "." + attr] = data.result;
		resolve(that.client.proxyContexts(data.result));
	    }
	});
    });
}

ObjectCache.prototype.registerClass = function(name, readable, writable){ 
    this.states[name] = {};
    for (var i in readable) {
	var attr = readable[i];
	this.states[name][attr] = null;
    }
}

ObjectCache.prototype.handleUpdates = function(data) {
    if ("updates" in data && data["updates"]) {
	if ("entity" in data) {
	    for (var k in data["entity"]) {
		var entity = data["entity"][k];
		var hash = hashContext(entity["context"]);
		this.states[hash.bucket][hash.key] = entity;
	    }
	}

	if ("store" in data) {
	    for (var i in data["store"]) {
		var update = data["store"][i];
		$.extend(this.states["SharedClientDataStore"][0]["data"], update);
	    }
	}
    }
}
