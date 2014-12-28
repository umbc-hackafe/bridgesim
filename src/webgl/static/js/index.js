var camera, scene, renderer;

var minimap;

var ship;
var spin = true;

var mouseX = 0, mouseY = 0;

var windowHalfX = window.innerWidth / 2;
var windowHalfY = window.innerHeight / 2;

$(document).ready(function() {
    init();
    animate();
});


function init() {
    camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 1, 2000);
    camera.position.z = 50;

    // scene

    scene = new THREE.Scene();

    var ambient = new THREE.AmbientLight(0x101030);
    scene.add(ambient);

    var directionalLight = new THREE.DirectionalLight(0xffeedd);
    directionalLight.position.set(0, 0, 1);
    scene.add(directionalLight);

    // model

    var onProgress = function(xhr) {
        if(xhr.lengthComputable) {
            var percentComplete = xhr.loaded / xhr.total * 100;
            console.log(Math.round(percentComplete, 2) + '% downloaded');
        }
    };

    var onError = function(xhr) {
    };

    THREE.Loader.Handlers.add(/\.dds$/i, new THREE.DDSLoader());

    var loader = new THREE.OBJMTLLoader();
    loader.load('models/ev_venator.obj', 'models/ev_venator.mtl', function(object) {
        scene.add(object);
        ship = object;
    }, onProgress, onError);

    //

    renderer = new THREE.WebGLRenderer({canvas: $("#main-canvas").get(0)});
    renderer.setSize(window.innerWidth, window.innerHeight);

    $(document).mousemove(onDocumentMouseMove);

    //

    $(window).resize(onWindowResize);

    $("#center-btn").click(function() { spin = !spin; });
}

function onWindowResize() {
    windowHalfX = window.innerWidth / 2;
    windowHalfY = window.innerHeight / 2;

    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();

    renderer.setSize(window.innerWidth, window.innerHeight);
}

function onDocumentMouseMove(event) {
    mouseX = (event.clientX - windowHalfX) / 2;
    mouseY = (event.clientY - windowHalfY) / 2;
}

//

function animate() {
    requestAnimationFrame(animate);
    render();
}

function render() {
    camera.position.x += (mouseX - camera.position.x) * .05;
    camera.position.y += (-mouseY - camera.position.y) * .05;

    camera.lookAt(scene.position);

    if(spin)
        ship.rotation.y += .01;

    renderer.render(scene, camera);
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

$(function() {
    window.client = new Client(location.hostname, 9000, "/client");
    //window.client.init(location.hostname, 9000, "/client");

    window.client.socket.addOnOpen(function(evt) { console.log("WebSocket is open!"); registerWithServer();});
    window.client.socket.addOnClose(function(evt) { console.log("Socket CLOSED!"); });
    //window.client.socket.addOnMessage(function(data) { console.log(data); });

    $("#test-btn").click(function() {
	window.client.call("Ship__name", ["Ship", 0, 1], {callback: function(res) {
	    $("#result-text").val(res.result);
	}, args: [prompt("Ship Name")]});
    });

    $("#update-enable").change(function() {
	window.client.call("ClientUpdater__requestUpdates", ["ClientUpdater", 0], {args: ["entity", this.checked ? parseInt($("#update-freq").val()) : 0]});
    });
    $("#update-freq").change(function() {
	if ($("#update-enable").prop("checked")) {
	    window.client.call("ClientUpdater__requestUpdates", ["ClientUpdater", 0], {args: ["entity", parseInt($(this).val())]});
	}
    });

    var mapWidth = $("#minimap").width();
    var mapHeight = $("#minimap").height();

    minimap = $("#minimap")[0].getContext("2d");
    minimap.fillStyle="#ff0000";
    //minimap.fillRect(0, 0, mapWidth, mapHeight);

    minimap.moveTo(0, 0);
    minimap.lineTo(mapWidth, 0);
    minimap.lineTo(mapWidth, mapHeight);
    minimap.lineTo(0, mapHeight);
    minimap.lineTo(0, 0);

    minimap.strokeStyle = "#ffffff";
    minimap.stroke();
});
