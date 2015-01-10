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

    $('#minimap-zoom-in').click(function() {
        minimap.zoomIn(2);
    });
    $('#minimap-zoom-out').click(function() {
        minimap.zoomIn(0.5);
    });
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

    if(spin && ship && "rotation" in ship)
        ship.rotation.y += .01;

    renderer.render(scene, camera);
}

$(function() {
    $(".conn-required").prop("disabled", true);

    minimap = new Map($("#minimap")[0], {x: 0, y: 0},
            {sizeX: 2000, sizeY: 2000})

    window.client = new Client(location.hostname, 9000, "/client",
        function() {
            // Request updates about entities in the Universe.
            window.client.$ClientUpdater.requestUpdates("entity", 15);

            // Add some callbacks for logging.
            $(".conn-required").prop("disabled", false);
            window.client.socket.addOnOpen(function(evt) {
                console.log("WebSocket is open!");
                $(".conn-required").prop("disabled", false);
            });
            window.client.socket.addOnClose(function(evt) {
                console.log("WebSocket is CLOSED!");
                $(".conn-required").prop("disabled", true);
            });

            // Send entity updates to the minimap.
            window.client.socket.addOnMessage(function(data) {
                minimap.updateFromData(data);
            });
            $("#test-btn").click(function() {
                window.client.call("Ship__name", ["Ship", 0, 1], {callback:
                    function(res) {
	                    $("#result-text").val(res.result);
	                },
                    args: [ prompt("Ship Name") ]
                });
            });
    });

});
