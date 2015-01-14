var minimap;

$(document).ready(function() {
    resize();
});

window.addEventListener('resize', resize);
function resize() {
    $('#minimap').prop('width', window.innerWidth);
    $('#minimap').prop('height', window.innerHeight);
    if (typeof minimap != 'undefined') {
        minimap.rescale(window.innerWidth, window.innerHeight);
    }
}


function initClient() {
    //window.client.init(location.hostname, 9000, "/client");
    window.client.$ClientUpdater.requestUpdates("Entity", 10)

    window.client.socket.addOnMessage(function(data) {
        minimap.updateFromData(data);
    });
}

$(function() {
    window.client = ScreenClient(initClient);

    minimap = new Map(window.client, $("#minimap")[0], {x: 0, y: 0, z: 0},
            {sizeH: 10000, sizeW: 10000});
});
