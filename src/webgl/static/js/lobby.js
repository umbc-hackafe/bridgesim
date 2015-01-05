function registerWithServer() {
    $("#center-btn").click(function() {
	window.client.call("whoami", null, {
	    callback: function(res) {
		console.log("You are " + res.result);
	    }
	})});
}

function handleUpdates(data) {
    if ("updates" in data && data["updates"]) {
	if ("lobby" in data) {
	    
	}
    }
}

function loadUniverses() {
    window.client.call("universes", null, {
	callback: function(res) {
	    window.universes = res.result;
	    for (k in window.universes) {
		var universe = window.universes[k];
		console.log(universe.name);
		$("#universe").append($("<option>").attr("value", universe.id).text(universe.name))
		$(".universe-required").show();
	    }
	    console.log(window.universes);
	    loadShips();
	},
	expand: true
    });
}

function loadShips() {
    for (var k in window.universes[0].entities) {
	var ctx = window.universes[0].entities[k];
	if (ctx[0] == "Ship") {
	    window.client.call("expand", ctx, {
		callback: function(res) {
		    console.log("Ship result", res.result);
		    $("#ship").append($("<option>").attr("value", res.result.id).text(res.result.name));
		}
	    });
	}
    }
    $(".ship-required").show();
}

$(function() {
    $('[class*="-required"]').hide();

    $("#universe").change(function() {
    });

    $("#lobby-form input[name=role]").change(function() {
	console.log("blah");
	if ($("#lobby-form input[name=role]:checked").length) {
	    console.log("ok");
	    $(".role-required").show();
	} else {
	    console.log("not ok");
	    $(".role-required").hide();
	}
    });

    window.client = new Client(location.hostname, 9000, "/client");
    window.client.socket.addOnOpen(function(evt) {
	console.log("WebSocket is open!");
	registerWithServer();
	window.client.call("whoami", null, {
	    callback: function(res) {
		console.log("We are " + res.result);
		document.cookie="clientid=" + res.result;
		$(".conn-required, .id-required").show();
	    }
	});
	loadUniverses();
    });

    window.client.socket.addOnClose(function(evt) {
	console.log("Socket CLOSED!");
	$(".conn-required").prop("disabled", true);
    });

    window.client.socket.addOnMessage(handleUpdates);
});
