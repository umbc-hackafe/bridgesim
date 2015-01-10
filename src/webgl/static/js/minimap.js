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
    window.client.$ClientUpdater.requestUpdates("entity", 10)

    window.client.socket.addOnMessage(function(data)
            {minimap.updateFromData(data);});
}

$(function() {
    window.client = ScreenClient(initClient);

    minimap = new Map($("#minimap")[0], {x: 0, y: 0}, {sizeX: 2000,
        sizeY: 2000}) ;
    //minimap.drawBlip(500, 1000);

    console.log(minimap.getSectorName(0,0,0));
    console.log(minimap.getSectorName(5000000,2000000,36000000));
});
