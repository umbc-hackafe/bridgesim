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
        minimapXY.zoomIn(2);
        minimapYZ.zoomIn(2);
        minimapXZ.zoomIn(2);
    });
    $('#minimap-zoom-out').click(function() {
        minimapXY.zoomIn(0.5);
        minimapYZ.zoomIn(0.5);
        minimapXZ.zoomIn(0.5);
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
    minimapXY = new Map($("#minimap-xy")[0], {x: 0, y: 0, z: 0},
            {planeW: "x", planeH: "y", sizeW: 5000, sizeH: 5000})
    minimapYZ = new Map($("#minimap-yz")[0], {x: 0, y: 0, z: 0},
            {planeW: "y", planeH: "z", sizeW: 5000, sizeH: 5000})
    minimapXZ = new Map($("#minimap-xz")[0], {x: 0, y: 0, z: 0},
            {planeW: "x", planeH: "z", sizeW: 5000, sizeH: 5000})

    window.client = ScreenClient(function() {
            // Request updates about entities in the Universe.
            window.client.$ClientUpdater.requestUpdates("entity", 15);

            // Send entity updates to the minimap.
            window.client.socket.addOnMessage(function(data) {
                minimapXY.updateFromData(data);
                minimapYZ.updateFromData(data);
                minimapXZ.updateFromData(data);
            });

            // Trigger map-lock button when pressing enter from the
            // textbox.
            $("#map-lock-target").change(function(e) {
                console.log(e);
                minimapXY.anchorTarget($("#map-lock-target").val());
                minimapYZ.anchorTarget($("#map-lock-target").val());
                minimapXZ.anchorTarget($("#map-lock-target").val());
            });

            // Lock the minimap automatically if the player is attached
            // to a ship.
            minimapXY.autoAnchorPlayer(window.client);
            minimapYZ.autoAnchorPlayer(window.client);
            minimapXZ.autoAnchorPlayer(window.client);

            // $("#test-btn").click(function() {
            //     window.client.call("Ship__name", ["Ship", 0, 1], {callback:
            //         function(res) {
	                    // $("#result-text").val(res.result);
	                // },
            //         args: [ prompt("Ship Name") ]
            //     });
            // });
    });

});
