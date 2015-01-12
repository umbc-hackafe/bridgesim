var minimap;

$(document).ready(function() {
    resize();
});

window.addEventListener('resize', resize);
function resize() {
    // $('#minimap').width = window.innerWidth;
    // $('#minimap').height = window.innerHeight;
    newWidth = $('#weapons-viewport').width();
    newHeight = $('#weapons-viewport').height();
    console.log("New width and height: ", newWidth, newHeight);
    $('#minimap').prop('width', newWidth);
    $('#minimap').prop('height', newHeight);
    if (typeof minimap != 'undefined') {
        minimap.rescale(newWidth, newHeight);
    }
}

function registerWithServer() {
    //window.client.socket.send({"message": "Hello, socket!"});
    $("#center-btn").click(function() {
	window.client.call("whoami", null, {
	    callback: function(res) {
		console.log("You are " + res.result);
	    }
	})});
}

function initClient() {
    //window.client.init(location.hostname, 9000, "/client");
    window.client.$ClientUpdater.requestUpdates("entity", 10);

    window.client.socket.addOnOpen(function(evt) {
	    registerWithServer();
	    window.client.call("whoami", null, {
	        callback: function(res) {
		    console.log("We are " + res.result);
		    document.cookie="clientid=" + res.result;
	        }
	    });
    });

    // Lock the minimap automatically if the player is attached
    // to a ship.
    minimap.autoAnchorPlayer(window.client);

    window.client.socket.addOnMessage(function(data)
            {minimap.updateFromData(data);});
}

$(function() {
    window.client = ScreenClient(initClient);

    minimap = new Map($("#minimap")[0], {x: 0, y: 0},
            {sizeX: 10000, sizeY: 10000}) ;
    //minimap.drawBlip(500, 1000);

    console.log(minimap.getSectorName(0,0,0));
    console.log(minimap.getSectorName(5000000,2000000,36000000));
});
