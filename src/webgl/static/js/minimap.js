var minimap;

$(document).ready(function() {
    resize();
});

window.addEventListener('resize', resize);
function resize() {
    $('#minimap').prop('width', window.innerWidth);
    $('#minimap').prop('height', window.innerHeight);
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

function handleUpdates(data) {
    if ("updates" in data && data["updates"]) {
	minimap.clear();
	if ("entity" in data) {
	    var entities = data["entity"];
	    for (i in entities) {
		var entity = entities[i];
		minimap.drawBlip(entity.location[0], entity.location[1], {});
	    }
	}
    }
}

$(function() {
    $(".conn-required").prop("disabled", true);

    window.client = new Client(location.hostname, 9000, "/client");
    //window.client.init(location.hostname, 9000, "/client");

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
    });

    window.client.socket.addOnMessage(handleUpdates);

    $("#update-enable").change(function() {
	window.client.call("ClientUpdater__requestUpdates", ["ClientUpdater", 0], {args: ["entity", this.checked ? parseInt($("#update-freq").val()) : 0]});
    });
    $("#update-freq").change(function() {
	if ($("#update-enable").prop("checked")) {
	    window.client.call("ClientUpdater__requestUpdates", ["ClientUpdater", 0], {args: ["entity", parseInt($(this).val())]});
	}
    });

    minimap = new Map($("#minimap")[0], {x: 0, y: 0}, {scale: 0.1});
    //minimap.drawBlip(500, 1000);

    // var mapcanvas = document.getElementById("minimap");

    // mapcanvas.width  = window.innerWidth;
    // mapcanvas.height = window.innerHeight;

    console.log(minimap.getSectorName(0,0,0));
    console.log(minimap.getSectorName(5000000,2000000,36000000));
});
