function handleUpdates(data) {
    if ("updates" in data && data["updates"]) {
        for (var keyval in data["store"]) {
	        if ("lobby-connected-players" in keyval) {
                console.log("Updating player list.");
                $("#player-list").html(
                        keyval["lobby-connected-players"].join("<br />"));
	        }
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
		    $("#ship-name").val($("#ship :selected").text());
		    $(".ship-required").show();
		}
	    });
	}
    }
}

$(function() {
    $(".hide-connected").show();
    console.log("Hiding .show-connected");
    $(".show-connected").hide();

    $("#join-lobby-btn").on('click', function() {
        // If there is a connection already open, close it.
        if (typeof window.client != 'undefined' &&
                window.client.socket.open) {
            console.log("Closing old connection.");
            window.client.socket.close();
        }

        console.log("Entering lobby with username " +
                $("#player-name").val());

        window.client = new Client(location.hostname, 9000, "/client",
                function() {
            console.log("WebSocket connected!");
            $(".show-connected").show();
            $(".hide-connected").hide();

            window.client.socket.addOnClose(function() {
                console.log("WebSocket DISCONNECTED!");
                $(".show-connected").hide();
                $(".hide-connected").show();
            });

            // Every time we receive an update, send it over to
            // handleUpdates.
            window.client.socket.addOnMessage(handleUpdates);
            window.client.$ClientUpdater.requestUpdates("store", 20);

            // Send the current player name to the shared data store.
            window.client.$SharedClientDataStore.list_append(
                    "lobby-connected-players", $("#player-name").val()).then(
                    function(data) {
                        if (data[0] == true) {
                        console.log("Updating player list.");
                        $("#player-list").html(data[1].join("<br />"));
                        }
                    });

            // Update the list of connected player names at least once.
            // window.client.$SharedClientDataStore.get(
            //         "lobby-connected-players").then(function(data) {
            //     $("#player-name").val(data.join("<br />"));
            // });
        });
    });

    // $("#lobby-form")[0].reset();
    $('[class*="-required"]').hide();

    $("#universe").change(function() {
    });

    $("#ship").change(function() {
	$("#ship-name").val($("#ship :selected").text());
    });

    $("#ship-name").keyup(function() {
	$("#ship :selected").text($("#ship-name").val());
    });

    $("#ship-name").change(function() {
	if ($("#ship :selected").val()) {
	    window.client.call("Ship__name", ["Ship", parseInt($("#universe :selected").val()), parseInt($("#ship :selected").val())], {
		args: [$("#ship-name").val()],
		callback: function(res) {
                    console.log("rename gave ", res);
		}
	    });
	} else {
	    console.log("Ship not created yet, waiting to update");
	}
    });

    $("#lobby-form input[name=role]").change(function(evt) {
	console.log(evt);
	console.log($(evt.target).prop("checked"));
	console.log("target", $(evt.target));
	if ($(evt.target).prop('checked')) {
	    var filters = {not_contains: window.clientID};
	    if (evt.target.dataset.maxPlayers) {
		console.log("It has max players: " + evt.target.dataset.maxPlayers);
		filters["len_lt"] = parseInt(evt.target.dataset.maxPlayers);
	    }

	    window.client.call("SharedClientDataStore__list_append", null, {
		args: ["lobby.ship-" + $("#universe :selected").val() + "-" + $("#ship :selected").val()
		       + ".role-" + evt.target.dataset.role, window.clientID],
		kwargs: filters,
		callback: function(res) {
		    console.log("list_append: ", res);
		}
	    });
	} else {
	    window.client.call("SharedClientDataStore__list_delete", null, {
		args: ["lobby.ship-" + $("#universe :selected").val() + "-" + $("#ship :selected").val()
		       + ".role-" + evt.target.dataset.role],
		kwargs: {value: window.clientID},
		callback: function(res) {
		    console.log("list_delete: ", res);
		}
	    });
	}

	console.log("blah");
	if ($("#lobby-form input[name=role]:checked").length) {
	    $(".role-required").show();
	} else {
	    $(".role-required").hide();
	    $("#ready").attr("checked", false);
	}
    });

    // window.client.socket.addOnOpen(function(evt) {
	// console.log("WebSocket is open!");
	// registerWithServer();
	// window.client.call("whoami", null, {
	    // callback: function(res) {
		// console.log("We are " + res.result);
		// document.cookie="clientid=" + res.result;
		// window.clientID = res.result;
		// $(".conn-required, .id-required").show();
	    // }
	// });
	// loadUniverses();
    // });

    // window.client.socket.addOnClose(function(evt) {
	// console.log("Socket CLOSED!");
	// $(".conn-required").prop("disabled", true);
    // });

    // window.client.socket.addOnMessage(handleUpdates);
});
