function SocketWrapper(socket) {
    this.socket = socket;
    this.queuedData = [];
    this.onOpens = [];
    this.onMessages = [];
    this.onErrors = [];
    this.onCloses = [];
    this.open = false;
    this.closed = false;
    this.wrap(socket);
}

SocketWrapper.prototype.wrap = function(socket) {
    var that = this;
    socket.onmessage = function(evt) {that.__doOnMessage(evt);};
    socket.onerror = function(evt) {that.__doOnError(evt);};
    socket.onclose = function(evt) {that.__doOnClose(evt);};
    socket.onopen = function(evt) {that.__doOnOpen(evt);};
}

SocketWrapper.prototype.__doOnOpen = function(evt) {
    // Log the socket opening.
    console.log("WebSocket opened!")

    this.open = true;
    this.closed = false;
    // APPARENTLY, this is now socket.this
    for (var l in this.onOpens.slice(0)) {
	this.onOpens[l](evt);
    }

    for (var d in this.queuedData) {
	this.send(this.queuedData[d]);
    }
    this.queuedData = [];
}

SocketWrapper.prototype.__doOnMessage = function(evt) {
    var jsonData = JSON.parse(evt.data);
    console.log("Receiving: ", jsonData);
    if (jsonData == null) {
	console.log("Data is null... that's weird.");
    } else {
	for (var l in this.onMessages.slice(0)) {
	    // Might need to do atob() here?
	    this.onMessages[l](jsonData);
	}
    }
}

SocketWrapper.prototype.__doOnError = function(evt) {
    for (var l in this.onErrors.slice(0)) {
	this.onErrors[l](evt);
    }
}

SocketWrapper.prototype.__doOnClose = function(evt) {
    // Log the closing
    console.log("WebSocket closed!");

    this.open = false;
    this.closed = true;

    for (var l in this.onCloses.slice(0)) {
	this.onCloses[l](evt);
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

    this.reconnect = true;
    this.reconnectAttempts = 0;
    this.reconnectWait = 1000;
    this.reconnectTimer = -1;
    this.init(host, port, path);
}

Client.prototype.doReconnectInterval = function(host, port, path) {
    var client = this;
    if (this.reconnect && !this.socket.open && this.socket.closed) {
	this.socket.wrap(new WebSocket("ws://" + host + ":" + port + (path[0] == "/" ? path : "/" + path)));

	console.log("Trying again in " + (this.reconnectWait/1000) + "s...");
	this.reconnectTimer = setTimeout(function() {
	    client.doReconnectInterval(host, port, path);
	}, this.reconnectWait);

	this.reconnectAttempts++;

	if (this.reconnectAttempts > 5 && this.reconnectAttempts <= 13)
	    this.reconnectWait *= 2;
    } else if (this.socket.open && !this.socket.closed) {
	console.log("Reconnected!");
    }
};

Client.prototype.startReconnect = function(host, port, path) {
    var client = this;
    if (client.reconnect && client.reconnectAttempts == 0) {
	this.doReconnectInterval(host, port, path);
    }
};

Client.prototype.init = function(host, port, path) {
    if (this.socket) this.socket.close();
    this.socket = new SocketWrapper(new WebSocket("ws://" + host + ":" + port + (path[0] == "/" ? path : "/" + path)));
    var client = this;

    var addReconnector = function(host, port, path) {
	client.socket.addOnClose(function(evt) {
	    if (evt && evt.code == 1001) {
		console.log("Server has closed! Will not reconnect.");
	    } else {
		client.startReconnect(host, port, path);
	    }
	});
    };
    addReconnector(host, port, path);

    this.socket.addOnOpen(function() {
	if (client.reconnectTimer != -1) {
	    clearTimeout(client.reconnectTimer);
	    client.reconnectTimer = -1;
	    client.reconnectAttempts = 0;
	    client.reconnectWait = 1000;
	}

	client.cache = new ObjectCache(client, client.socket, function() {
	    client.call("functions", null, {
		callback: function(data) {
		    client.loadFunctions(data.result);
		    client.call("specials", null, {
			callback: function(data) {
			    client.loadSpecials(data.result);
			    client.call("whoami", null, {
				callback: function(data) {
				    client.id = data.result;
				    console.log("Done initializing client!");
				    if (client.doneCB) client.doneCB();
				}
			    });
			}
		    });
		}
	    });
	});
	client.call("ClientUpdater__fullSync", null);
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
    this.proxyClasses = {};

    for (var className in map) {
	var readable = map[className]["readable"];
	var writable = map[className]["writable"];
	var methods = map[className]["methods"];
	var isGlobal = !map[className]["context"];

	this.cache.registerClass(className, readable, writable);

	var fffffffuuuuuuuuuuuu = function(className, readable, writable, cache) {
	    client.proxyClasses[className] = function(ctx) {
		this.context = ctx;
		var proxy = this;

		for (var i in readable) {
		    var attr = readable[i];
		    var isWritable = writable.indexOf(attr) >= 0;
		    var aNewFunction = function(theObj, theAttr, theIW, theCache) {
			Object.defineProperty(theObj, theAttr, {
			    get: function() {
				var res = theCache.get(this.context, className, theAttr);
				return res;
			    },
			    set: function(val) {
				var res;
				if (theIW) {
                    res = theCache.set(this.context, className, theAttr,
                            val, {});
				    proxy["__set_" + theAttr](res, {});
				} else {
				    res = Error(className + "." + theAttr + " is not writable");
				}
				return res;
			    }
			});
		    };
		    aNewFunction(this, attr, isWritable, cache);
		}
	    };
	};
	// I assure you this name is quite appropriate
	fffffffuuuuuuuuuuuu(className, readable, writable, this.cache);

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

	    var remoteName = methodsAndWritable[i];

	    // Did I mention...
	    var f = function(clsName, pName, rName) {
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
			    client.call(clsName + "__" + rName,
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
	    f(className, prop, remoteName);
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
    this.reconnect = false;
    this.socket.close();
}

function hashContext(context) {
    if (context) {
	return {bucket: context[0],
		key: context.length > 1 ? context.slice(1).join(".") : 0};
    } else {
	return 0;
    }
}

function ObjectCache(client, socket, onDone) {
    this.client = client;
    this.socket = socket;

    this.states = {};
    this.synced = false;
    this.onDone = onDone;

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
    this.socket.addOnMessage(function(data) {that.handleUpdates(data);});
}

ObjectCache.prototype.set = function(context, cls, attr, val) {
    var hash = hashContext(context);
    var that = this;

    if (hash == 0) {
	hash = {bucket: cls, key: 0};
    }

    if (!(hash.bucket in this.states))
	this.states[hash.bucket] = {};
    if (!(hash.key in this.states[hash.bucket]))
	this.states[hash.bucket][hash.key] = {};

    this.states[hash.bucket][hash.key][attr] = val;
    return val;
};

ObjectCache.prototype.get = function(context, cls, attr) {
    var hash = hashContext(context);
    var that = this;

    if (hash == 0) {
	hash = {bucket: cls, key: 0};
    }

    if (hash.bucket in this.states) {
	if ((hash.key) in this.states[hash.bucket]) {
	    if (attr in this.states[hash.bucket][hash.key]) {
		return this.client.proxyContexts(this.states[hash.bucket][hash.key][attr]);
	    } else console.warn("Cache object", this.states[hash.bucket][hash.key], "has no attr named", attr);
	} else console.warn("Cache bucket", this.states[hash.bucket], "has no object for context", hash.key);
    } else console.warn("Cache", this.states, "has no bucket for type", hash.bucket);

    console.error("Did not find specified key", attr, "in context", context, "(cls=", cls, ")");
    if (hash.bucket in this.states && hash.key in this.states[hash.bucket]) {
	console.info("The object's cache is", this.states[hash.bucket][hash.key]);
    }
    return null;
}

ObjectCache.prototype.registerClass = function(name, readable, writable){ 
    if (!(name in this.states))
	this.states[name] = {};
}

ObjectCache.prototype.handleUpdates = function(data) {
    console.log("Got updates", data);
    if (("updates" in data && data["updates"]) || ("fullsync" in data && data["fullsync"])) {
	if ("fullsync" in data)
	    console.log("==== Start Fullsync ====");
	for (var k in data) {
	    if (k != "updates" && data.hasOwnProperty(k)) {
		console.log("Handling", k, "updates");
		for (var i in data[k]) {
		    var killme = function(that, datas, l, j) {
			var hash;
			if ("context" in datas[l][j]) {
			    hash = hashContext(datas[l][j].context);
			    if (hash == 0) {
				hash = {bucket: l, key: 0};
			    }
			} else {
			    console.log("No context in ", datas[l][j]);
			    console.log("Setting hash to bucket:", l, "key", 0);
			    hash = {bucket: l, key: 0};
			}
			if (!(hash.bucket in that.states))
			    that.states[hash.bucket] = {};

			if (!(hash.key in that.states[hash.bucket]))
			    that.states[hash.bucket][hash.key] = {};

			$.extend(that.states[hash.bucket][hash.key], datas[k][i]);
		    };
		    killme(this, data, k, i);
		}
	    }
	}
    }
    if ("fullsync" in data && data["fullsync"]) {
	console.log("==== End Fullsync ====");
	console.log("Got a fullsync!");
	if (this.onDone) {
	    this.onDone();
	}
    }
}
