function ScreenClient(callback) {
    var client =  new Client(location.hostname, location.port,
            "/client", function() {
                document.cookie = "clientid=" + client.id;
                callback();
            });

    client.socket.addOnOpen(function() {
        changeStyleState("open");
    });
    client.socket.addOnClose(function() {
        changeStyleState("closed");
    });
    return client;
}

function changeStyleState(state) {
    if (state == "open") { // Socket OPENING
        // Show things which need to be shown on opening, hide things
        // that need to be shown on closing.
        $(".show-connected").show();
        $(".hide-connected").hide();
        
        // Enable fields which require a connection.
        $(".enable-connected").prop("disabled", false);
        $(".disable-connected").prop("disabled", true);
    } else { // Socket CLOSING
        // Do the inverse of the other operations.
        $(".show-connected").hide();
        $(".hide-connected").show();

        $(".enable-connected").prop("disabled", true);
        $(".disable-connected").prop("disabled", false);
    }
}
