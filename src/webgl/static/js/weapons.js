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
    $(".show-connected").show();
    $(".hide-connected").hide();
    //window.client.init(location.hostname, 9000, "/client");
    window.client.$ClientUpdater.requestUpdates("entity", 10);

    window.client.socket.addOnOpen(function(evt) {
	    console.log("WebSocket is open!"); registerWithServer();
	    $(".conn-required").prop("disabled", false);
	    window.client.call("whoami", null, {
	        callback: function(res) {
		    console.log("We are " + res.result);
		    document.cookie="clientid=" + res.result;
	        }
	    });
    });

    window.client.socket.addOnClose(function(evt) {
	console.log("Socket CLOSED!");
	    $(".conn-required").prop("disabled", true);
        $(".show-connected").hide();
        $(".hide-connected").show();
    });

    window.client.socket.addOnMessage(function(data)
            {minimap.updateFromData(data);});
}

$(function() {
    $(".conn-required").prop("disabled", true);
    $(".show-connected").hide();
    $(".hide-connected").show();

    window.client = new Client(location.hostname, 9000, "/client", initClient);

    minimap = new Map($("#minimap")[0], {x: 0, y: 0}, {sizeX: 2000,
        sizeY: 2000}) ;
    //minimap.drawBlip(500, 1000);

    console.log(minimap.getSectorName(0,0,0));
    console.log(minimap.getSectorName(5000000,2000000,36000000));
});
