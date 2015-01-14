var shipOptions = {};


function handleUpdates(data) {
    if ("updates" in data && data["updates"]) {
        console.log("Got update");
	    if ("Player" in data) {
            loadPlayers();
	    }
    }
}

function loadUniverses() {
    window.client.$Specials.universes().then(function(data) {
	    window.universes = data;
        var waitingPromises = window.universes.length;
	    for (k in window.universes) {
		    var universe = window.universes[k];
            universe.name.then(function(name) {
		        console.log("Loading universe: ", name);
                // TODO: use universe.id here
                var id = universe.context[1];
                console.log("ID " + id);
                $("#universe").append($("<option>").attr("value",
                            id).text(name));

                // Keep track of the number of universes that have been
                // loaded, and if they are done, check to see if the
                // player has one set already. If so, select that
                // universe.
                waitingPromises--;
                if (waitingPromises == 0) {
                    window.client.$Client.player.then(function(myplayer) {
                        if(myplayer)
                            myplayer.universe.then(function(universe) {
                                if (universe) {
                                    $("#universe").val(universe.context[1]);
                                    $("#universe").change();
                                }
                            });
                    });
                }
            });
	    }

    });

}

function loadShips(universeID) {
    window.universes[universeID].entities.then(function(entities) {
        console.log("Loading ships from " + universeID);
        console.log(JSON.stringify(entities));
        for (var k in entities) {
            var entity = entities[k];
            //var loadShip = function(entity) {
                if (entity.context[0] == "Ship") {
                    entity.name.then(function(name) {
                    console.log("Loading ship: " + name);
                    shipOptions[name] = entity.context;
                    $("#ship").append($("<option>").attr("value",
                                entity.context[2]).text(name));
                    $("#ship-name").val($("#ship :selected").text());

                    $("#ships-waiting").append($("<div>")
                            .addClass("ship-crew-box")
                            .attr("id", "#ship-opt-" + name)
                        );

                    });
                }
            //}
            //loadShip(entity);
        }
    });
}

function loadPlayers() {
    window.client.$Specials.players().then(function(players) {
        var playerlist = $("#lobby-players").html('<ul></ul>').find('ul');
        for (var k in players) {
            var player = players[k];
            console.log(player);
            player.name.then(function(name) {
                // If the name is falsey, use a placeholder.
                if (!name) {
                    name = "Unnamed Player";
                }
                console.log("Listing player: " + name);
                playerlist.append("<li>" + name + "</li>");
            });
        }
    });
    window.client.$Client.player.then(function(myplayer) {
        if(myplayer)
            myplayer.name.then(function(name) {
                $("#player-name").val(name);
            });
    });
}

$(function() {
    // There is no point for the form to be submitted to, so disallow
    // submission.
    $("#lobby-form").submit(false);

    // Make sure the form is clear.
    $("#lobby-form")[0].reset();

    // Hide any elements that are not yet relevant.
    $(".universe-required").hide();
    $(".ship-required").hide();
    $(".role-required").hide();
    $(".role-helm-required").hide();
    $(".some-role-helm-required").hide();

    $("all-ready-enable").attr("disabled", true)

    $("#player-name").change(function() {
        // On an enter key pressed...
        // Set the player's name according to the value. It will be
        // cached locally, so we don't have to worry about waiting
        // for the server to get the update.
        var newname = $("#player-name").val();
        console.log("New player name: " + newname);
        window.client.$Client.player.then(function(player) {
            player.name = newname;
        });

        // Reload the player list.
        loadPlayers();
    });


    $("#universe").change(function() {
        // Get the universe ID from the selector, and set the player's
        // universe to it.
        var universeid = $("#universe :selected").attr("value");
        console.log(universeid);
        client.$Client.player.then(function(player) {
            console.log("Setting player universe");
            player.universe = {context: ["Universe", universeid]};
        });

        // Show any elements that required the universe.
        $(".universe-required").show();

        // Load the ships from the selected universe.
        loadShips(universeid);
    });

    $("#ship").change(function() {
        var shipname = $("#ship :selected").text();
        console.log("Selecting ship " + shipname);
	    $("#ship-name").val(shipname);
        $(".ship-required").show();
        console.log(shipOptions[shipname]);

        client.$Client.player.then(function(player) {
            // TODO: When the server supports direct context parsing,
            // send the context alone without the wrapper.
            player.ship = {context: shipOptions[shipname]};
        });
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

	if ($("#lobby-form input[name=role]:checked").length) {
	    $(".role-required").show();
	} else {
	    $(".role-required").hide();
	    $("#ready").attr("checked", false);
	}

    $("#lobby-form input[name=role]:checked").each(function() {
        var role = $(this).attr("value");
        console.log("Showing role: " + role);
        $(".role-" + role + "-required").show();
    });
    $("#lobby-form input[name=role]:not(:checked)").each(function() {
        var role = $(this).attr("value");
        console.log("Unshowing role: " + role);
        $(".role-" + role + "-required").hide();
    });

    });

    // Cause the ready checkbox to trigger the change function.
    $("#ready-box").trigger("change");
    $("#ready-box").change(function() {
        // Check if the box is checked. If so, enable the ready button.
        // TODO: in the future, this should check all players' ready
        // statuses
        var disable = true;
        if ($("#ready-box input:checkbox:checked").length > 0) {
            disable = false;
        }
        $(".all-ready-enable").attr("disabled", disable);
    });

    $("#enter-game").click(function() {
        window.location.href = "/weapons";
        return false;
    });

    window.client = ScreenClient(function() {
	    loadUniverses();
        loadPlayers();
    });

    window.client.socket.addOnMessage(handleUpdates);
    window.client.$ClientUpdater.requestUpdates("Player", 50);
});
