function identify(num, chars) {
    l = chars.length;
    r = "";
    do {
	r = chars[num % l] + r;
	num = Math.trunc(num / l);
    } while (num > 0);
    return r
}

// Set a sector of 10 kilometers, because that's a good unit for space
// sizes.
// 1 au = 149597871000m
var sectorSize = 10000;
var subSectorSize = sectorSize/2;

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
// scaleW  : sets only X scale, in pixels-per-meter
// scaleH  : sets only Y scale, in pixels-per-meter
// sizeW   : sets the scale such that the map represensts a real width of (sizeW) m
// sizeH   : sets the scale such that the map represents a real height of (sizeH) m
//
// # Colors #
// borderColor  : sets the color of the map's borders
function Map(canvas, anchor, options) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d");
    this.anchor = {x: 0, y: 0, z: 0};
    this.targetid = -1;

    // Fill out missing coordinates with zero in the anchor.
    if (anchor)
        $.extend(this.anchor, anchor);

    if (typeof anchor === "function") {
	    this.getAnchor = this.anchor;
    } else {
	    this.getAnchor = function() {
	        return this.anchor;
	    }
    }

    // Retrieve the options for scaling, because they need to be used to
    // determine the height and width.
    this.opts = {
        planeW: "x",
        planeH: "y",
	    borderColor: "#ffffff",
        sectorLineWidth: 2,
        subSectorLineWidth: 1,
	    sectorColor: "#99f",
	    subSectorColor: "#55a",
	    sizeW: 10000, // X display width is 10000m
	    sizeH: 10000  // Y display width is 10000m
    };

    if (options)
	    $.extend(this.opts, options);

    this.sizeW = this.opts.sizeW;
    this.sizeH = this.opts.sizeH;

    this.rescale($(this.canvas).width(), $(this.canvas).height());
    this.redraw();
}

Map.prototype.rescale = function(width, height) {
    this.width = width;
    this.height = height;

    this.scaleW = this.width / this.sizeW;
    this.scaleH = this.height / this.sizeH;

    contains = [ this.cornerW(),
                 this.cornerH(),
                (this.cornerW() + this.width / this.scaleW),
                (this.cornerH() + this.height / this.scaleH) ]

    console.log("Map rescaled, contains [" + contains[0] + "," +
            contains[1] + "] to [" + contains[2] + "," + contains[3] +
            "]");
}

Map.prototype.redraw = function() {
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
    this.context.beginPath();
    this.context.moveTo(0, 0);
    this.context.lineTo(this.width, 0);
    this.context.lineTo(this.width, this.height);
    this.context.lineTo(0, this.height);
    this.context.lineTo(0, 0);

    this.context.strokeStyle = this.opts.borderColor;
    this.context.stroke();
}

Map.prototype.drawLines = function() {
    var minSubSectorX = subSectorSize * (Math.trunc(this.cornerW() /
                subSectorSize));
    var minSubSectorY = subSectorSize * (Math.trunc(this.cornerH() /
                subSectorSize));
    var xLoc = this.getDisplayLocation(minSubSectorX, this.cornerH());
    var yLoc = this.getDisplayLocation(this.cornerW(), minSubSectorY);

    while (yLoc.y <= this.height) {

        // If the y location falls on a full sector line, draw it with
        // the sector color. Otherwise, use a subsector.
        if (minSubSectorY % sectorSize == 0) {
            this.context.strokeStyle = this.opts.sectorColor;
            this.context.lineWidth = this.opts.sectorLineWidth;
        } else {
            this.context.strokeStyle = this.opts.subSectorColor;
            this.context.lineWidth = this.opts.subSectorLineWidth;
        }

	    if (this.isOnMap(this.cornerW(), minSubSectorY)) {
            this.context.beginPath();
	        this.context.moveTo(0+.5, yLoc.y+.5);
	        this.context.lineTo(this.width+.5, yLoc.y+.5);
	        this.context.stroke();
	    }

	    while (xLoc.x <= this.width) {
            // If the x location falls on a full sector line, draw it with
            // the sector color. Otherwise, use a subsector.
            if (minSubSectorX % sectorSize == 0) {
                this.context.strokeStyle = this.opts.sectorColor;
                this.context.lineWidth = this.opts.sectorLineWidth;
            } else {
                this.context.strokeStyle = this.opts.subSectorColor;
                this.context.lineWidth = this.opts.subSectorLineWidth;
            }

	        if (this.isOnMap(minSubSectorX, this.cornerH())) {
                this.context.beginPath();
		        this.context.moveTo(xLoc.x+.5, 0.5);
		        this.context.lineTo(xLoc.x+.5, this.height+.5);
		        this.context.stroke();
	        }

	        minSubSectorX += subSectorSize;
	        xLoc = this.getDisplayLocation(minSubSectorX, this.cornerH());
	    }
	    minSubSectorY += subSectorSize;
	    yLoc = this.getDisplayLocation(this.cornerW(), minSubSectorY);
    }
}

Map.prototype.drawBlip = function(x, y, options) {
    var opts = {color: "#ff0000",
		shape: "dot",
        radius: 5,
		label: "Ship"};

    if (options)
	$.extend(opts, options);

    if (this.isOnMap(x, y)) {
	var loc = this.getDisplayLocation(x, y);
	this.context.strokeStyle = opts.color;
	this.context.fillStyle = opts.color;

	if (opts.shape == "dot") {
	    this.context.beginPath();
        this.context.arc(loc.x, loc.y,
                opts.radius * (this.scaleW + this.scaleH) / 2,
                0, 2 * Math.PI, true);
	    this.context.fill();
	}
    } else {
	console.log("Not on map");
    }
}

Map.prototype.anchorTarget = function(targetid) {
    this.targetid = targetid;
}

// Shortcuts!
Map.prototype.anchorW = function() {
    return this.getAnchor()[this.opts.planeW];
}

Map.prototype.anchorH = function() {
    return this.getAnchor()[this.opts.planeH];
}

Map.prototype.cornerW = function() {
    return (this.anchorW() - this.width / (2 * this.scaleW));
}

Map.prototype.cornerH = function() {
    return (this.anchorH() - this.height / (2 * this.scaleH));
}

Map.prototype.getDisplayLocation = function(x, y) {
    return {x: (x - this.cornerW()) * this.scaleW,
	    y: (y - this.cornerH()) * this.scaleH};
}

Map.prototype.isOnMap = function(x, y) {
    var pos = this.getDisplayLocation(x, y);
    return pos.x >= 0 && pos.x < this.width &&
	pos.y >= 0 && pos.y < this.height;
}

Map.prototype.getSectorName = function(x, y, z) {
    return identify(Math.trunc(x/sectorSize), greek) + 
	identify(Math.trunc(y/sectorSize), num) +
	identify(Math.trunc(z/sectorSize), alpha);
}

Map.prototype.zoomIn = function(scale) {
    // The "size" of the map decreases as you zoom in.
    this.sizeW = this.sizeW / scale;
    this.sizeH = this.sizeH / scale;

    // Therefore, the scale of pixels to meters increases, because you
    // have the same pixels to display fewer meters.
    this.scaleW = this.scaleW * scale;
    this.scaleH = this.scaleH * scale;

    // Redraw
    console.log("Redrawing map with zoomed at " + 100 * scale + "%");
    this.redraw();
}

Map.prototype.updateFromData = function(data) {
    if ("updates" in data && data["updates"]) {
        minimap.redraw();
        if ("entity" in data) {
            var entities = data["entity"];
            for (i in entities) {
                var entity = entities[i];
                var entityLoc = {x: entity.location[0],
                    y: entity.location[1], z: entity.location[2]};
                if (entity.context[0] == "Ship") {
                    if (entity.id == this.targetid) {
                        this.anchor.x = entity.location[0];
                        this.anchor.y = entity.location[1];
                        this.anchor.z = entity.location[2];
                        properties["color"] = "#AAAAAA";
                    }
                    properties = { radius: entity.radius };
                    minimap.drawBlip(entityLoc[this.opts.planeW],
                        entityLoc[this.opts.planeH], properties);
                }
            }
        }
    }
}
