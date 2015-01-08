function identify(num, chars) {
    l = chars.length;
    r = "";
    do {
	r = chars[num % l] + r;
	num = Math.trunc(num / l);
    } while (num > 0);
    return r
}

// Set a sector of 1 kilometer, because that's the best unit
// 1 au = 149597871000m
var sectorSizeX = 1000;
var sectorSizeY = 1000;
var sectorSizeZ = 1000;

var alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
var num = "0123456789"
var greek = "\x03b1\x03b2\x03b3\x03b4\x03b5\x03b6\x03b7\x03b8\x03b9\x03ba\x03bb\x03bc\x03bd\x03be\x03bf\x03c0\x03c1\x03c2\x03c3\x03c4\x03c5\x03c6\x03c7\x03c8\x03c9\x03ca";

// Constructs and initializes a Map (mini or otherwise) within the
// given canvas. Anchor the top-left corner at a specific coordinate
// in space, which may either be constant (a map x,y:numbers), or
// dynamic (a function that returns a map x,y:numbers). Options is a
// map of attribute-values.

// Valid options:
// # Scaling #
// scale   : sets both X and Y scale, in pixels-per-meter
// scaleX  : sets only X scale, in pixels-per-meter
// scaleY  : sets only Y scale, in pixels-per-meter
// sizeX   : sets the scale such that the map represensts a real width of (sizeX) m
// sizeY   : sets the scale such that the map represents a real height of (sizeY) m
//
// # Colors #
// borderColor  : sets the color of the map's borders
function Map(canvas, anchor, options) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d");

    this.width = $(this.canvas).width();
    this.height = $(this.canvas).height();
    this.halfWidth = this.width / 2;
    this.halfHeight = this.height / 2;

    if (typeof anchor === "function") {
	    this.getAnchor = anchor;
    } else {
	    this.getAnchor = function() {
	        return anchor;
	    }
    }

    // Retrieve the options for scaling, because they need to be used to
    // determine the height and width.
    this.opts = {
	    borderColor: "#ffffff",
	    gridColor: "#003",
	    scale: 1 // 1px = 1m
    };

    if (options)
	    $.extend(this.opts, options);

    if (this.opts.scale) {
	    this.scaleX = this.opts.scale;
	    this.scaleY = this.opts.scale;
    }
    if (this.opts.scaleX)
	    this.scaleX = this.opts.scaleX;
    if (this.opts.scaleY)
	    this.scaleY = this.opts.scaleY;

    if (this.opts.sizeX)
	    this.scaleX = this.width / this.opts.sizeX;
    if (this.opts.sizeY)
        this.scaleY = this.height / this.opts.sizeY;



    contains = [ this.cornerX(),
                 this.cornerY(),
                (this.cornerX() + this.width / this.scaleX),
                (this.cornerY() + this.height / this.scaleY) ]

    console.log("Map initiated, contains [" + contains[0] + "," +
            contains[1] + "] to [" + contains[2] + "," + contains[3] +
            "]");

    this.clear();
    this.drawLines();
    this.drawUI();
}

Map.prototype.clear = function() {
    // Clear the whole canvas.
    this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);
}

Map.prototype.drawUI = function() {
    // Draw a border!
    this.context.moveTo(0, 0);
    this.context.lineTo(this.width, 0);
    this.context.lineTo(this.width, this.height);
    this.context.lineTo(0, this.height);
    this.context.lineTo(0, 0);

    this.context.strokeStyle = this.opts.borderColor;
    this.context.stroke();
}

Map.prototype.drawLines = function() {
    var minSectorX = sectorSizeX * (Math.trunc(this.cornerX() / sectorSizeX));
    var minSectorY = sectorSizeY * (Math.trunc(this.cornerY() / sectorSizeY));
    var xLoc = this.getDisplayLocation(minSectorX, this.cornerY());
    var yLoc = this.getDisplayLocation(this.cornerX(), minSectorY);

    this.context.strokeStyle = this.opts.gridColor;

    while (yLoc.y <= this.height) {
	if (this.isOnMap(this.cornerX(), minSectorY)) {
	    this.context.moveTo(0+.5, yLoc.y+.5);
	    this.context.lineTo(this.width+.5, yLoc.y+.5);
	    this.context.stroke();
	}

	while (xLoc.x <= this.width) {
	    if (this.isOnMap(minSectorX, this.cornerY())) {
		this.context.moveTo(xLoc.x+.5, 0.5);
		this.context.lineTo(xLoc.x+.5, this.height+.5);
		this.context.stroke();
	    }
	    minSectorX += sectorSizeX;
	    xLoc = this.getDisplayLocation(minSectorX, this.cornerY());
	}
	minSectorY += sectorSizeY;
	yLoc = this.getDisplayLocation(this.cornerX(), minSectorY);
    }
}

Map.prototype.drawBlip = function(x, y, options) {
    var opts = {color: "#ff0000",
		shape: "dot",
		label: "Ship"};

    if (options)
	$.extend(opts, options);

    if (this.isOnMap(x, y)) {
	var loc = this.getDisplayLocation(x, y);
	this.context.strokeStyle = opts.color;
	this.context.fillStyle = opts.color;

	if (opts.shape == "dot") {
	    this.context.beginPath();
	    this.context.arc(loc.x, loc.y, 5, 0, 2 * Math.PI, true);
	    this.context.fill();
	}
    } else {
	console.log("Not on map");
    }
}

// Shortcuts!
Map.prototype.anchorX = function() {
    return this.getAnchor().x;
}

Map.prototype.anchorY = function() {
    return this.getAnchor().y;
}

Map.prototype.cornerX = function() {
    return (this.getAnchor().x - this.halfWidth) / this.scaleX;
}

Map.prototype.cornerY = function() {
    return (this.getAnchor().y - this.halfHeight) / this.scaleY;
}

Map.prototype.getDisplayLocation = function(x, y) {
    return {x: (x - this.cornerX()) * this.scaleX,
	    y: (y - this.cornerY()) * this.scaleY};
}

Map.prototype.isOnMap = function(x, y) {
    var pos = this.getDisplayLocation(x, y);
    return pos.x >= 0 && pos.x < this.width &&
	pos.y >= 0 && pos.y < this.height;
}

Map.prototype.getSectorName = function(x, y, z) {
    return identify(Math.trunc(x/sectorSizeX), greek) + 
	identify(Math.trunc(y/sectorSizeY), num) +
	identify(Math.trunc(z/sectorSizeZ), alpha);
}

Map.prototype.zoom = function(scale) {
    this.scaleX = this.scaleX / scale;
    this.scaleY = this.scaleY / scale;

    // Redraw
    console.log("Redrawing map with scales at " + 100 / scale + "%");
    this.clear();
    this.drawLines();
    this.drawUI();
}
