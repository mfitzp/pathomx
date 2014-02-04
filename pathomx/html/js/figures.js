/* Helper functions */

/* Constant definitions for numpy -> Javascript compatibility */
nan = 0; //Number.NaN;
inf = 0; //Infinity;
None = 0; //null;

    function getWindowSize(){
        var w = window,
            d = document,
            e = d.documentElement,
            g = d.getElementsByTagName('svg')[0],
            q = typeof(QtViewportSize) == 'undefined' ? {'x':false,'y':false} : QtViewportSize;

            x = q.x || w.innerWidth || e.clientWidth || g.clientWidth,
            y = q.y || w.innerHeight|| e.clientHeight|| g.clientHeight;
        return [x,y]
    }
    
    function getElementSize(id){
        if (id == 'body' || id =='svg'){
            return getWindowSize();
        } else if (d3.select(id).attr('width')) {
            // Try attribute
            xy = [ d3.select(id).attr('width'), d3.select(id).attr('height') ]
            return xy
        } else {
            // Try offsetWidth
            xy = [        
                d3.select(id)[0][0].offsetWidth.parseInt(),
                d3.select(id)[0][0].offsetHeight.parseInt(),
                ];
            if (xy[1] == 0) { xy[1] = xy[0]*2/3; } //800*600
            return xy
        }
    }


    d3.unique = function(array, f) {
      return d3.nest().key(f || String).entries(array).map(function(d) { return d.key; });
    };
    
var insertLinebreaks = function (t, d, width) {
    console.log(t);
    var el = d3.select(t);
    var p = d3.select(t.parentNode);
    p.append("foreignObject")
        .attr('x', -width/2)
        .attr('y', 6)
        .attr("width", width)
        .attr("height", 200)
      .append("xhtml:p")
        .attr('style','word-wrap: break-word; text-align:center; -webkit-hyphens: auto; hyphens: auto;')
        .html(d);    

    el.remove();

};

    
/* Figure d3 functions */
function heatmap(id, buckets, scale){

    idxy = getElementSize(id)
    var width = idxy[0],
        height = idxy[1];
    
    // Buckets contains x,y,value data
    // id for resulting SVG object (can shift it somewhere else after) or may want to move object definition to parent

    buckets.forEach(function(d) {
        d.value = parseFloat(d.value);
    });
    var xlabels = d3.unique( buckets, function(d) { return d.x }),
        ylabels = d3.unique( buckets, function(d) { return d.y });

    var cellw = 18,
        cellh = 18;

    var height = (ylabels.length * 18) + 150;
    //width = (xlabels.length * 20) +150;
        
    var margin = {top: 100, right: 50, bottom: 50, left: width/2};



    var svg = d3.select(id)//.insert("svg",':first-child')
                .attr("class", 'heatmap')
                .attr("width", width) // + margin.left + margin.right)
                .attr("height", height) // + margin.top + margin.bottom)
                .attr('viewBox','0 0 ' + width + ' ' + height)
                .attr('preserveAspectRatio','xMidYMid')        
                
                //.attr("id", id)
                .append("g")
                .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

      // Coerce the CSV data to the appropriate types.



    var r = Math.max( 
            Math.abs( d3.min(buckets, function(d) { return d.value; } ) ), 
            Math.abs( d3.max(buckets, function(d) { return d.value; } ) )
            )
            
    // r is data extreme; but outliers can diminish scales to uselessness
    // Need to rescale to cover majority of data; stdev when implemented in d3;
    // may be better to pass scale in from main app (allow config/etc.)
    
    var x = d3.scale
                .ordinal()
                .domain(xlabels )
                .rangeBands([0, xlabels.length*cellw]),
        y = d3.scale
                .ordinal()
                .domain(ylabels)
                .rangeBands([0, ylabels.length*cellh]),
            
        z = d3.scale
            .pow()
            .exponent(.5)
//              .linear()
                .domain( [-r , 0, +r] )
                .range(["#2166ac","#f5f5f5","#b2182b"]);
                
    function safez(num){ return isNaN(num) ? "#ffffff" : z(num); } 

    // Display the tiles for each non-zero bucket.
    // See http://bl.ocks.org/3074470 for an alternative implementation.
    svg.selectAll(".tile")
      .data(buckets)
    .enter()
      .append("rect")
      .attr("class", "tile")
      .attr("x", function(d) { return x(d.x); })
      .attr("y", function(d) { return y(d.y); })
      .attr("width",cellw)
      .attr("height",cellh)
      .style("fill", function(d) { return safez(d.value); });


    // Add a legend for the color values.
    var legend = svg.selectAll(".legend")
      .data(z.ticks(6).slice(1).reverse())
    .enter().append("g")
      .attr("class", "legend")
      .attr("transform", function(d, i) { return "translate(" + (width - 50) + "," + (20 + i * 20) + ")"; });

    legend.append("rect")
      .attr("width", 20)
      .attr("height", 20)
      .style("fill", z);

    legend.append("text")
      .attr("x", 26)
      .attr("y", 10)
      .attr("dy", ".35em")
      .text(String);

    svg.append("text")
      .attr("class", "label")
      .attr("x", width + 20)
      .attr("y", 10)
      .attr("dy", ".35em")
      .text(scale);

    // Add an x-axis with label.
    xa = svg.append("g")
      .attr("class", "x axis")
      //.attr("transform", "translate(0," + height + ")")
      .call(d3.svg.axis().scale(x).orient("top"));

    xa.selectAll("text")             // Rotate x axis labels
            .style("text-anchor", "start")
            .attr("transform", "rotate(-65)" )
            .attr("x", "1em")
            .attr("y", "0em");

    // Add a y-axis with label.
    svg.append("g")
      .attr("class", "y axis")
      .call(d3.svg.axis().scale(y).orient("left"));

    svg.selectAll(".y .tick").each(function(d) {
        d3.select(this)
            .attr('style','cursor:pointer;')
            .on("click",function(d){ delegateLink('metapath://db/metabolite/'+d+'/view'); });
    });

};


function circos(id, matrix, labels, urls){

    // From http://mkweb.bcgsc.ca/circos/guide/tables/

    var chord = d3.layout.chord()
        .padding(0.05)
        .sortSubgroups(d3.descending)
        .matrix(matrix);

        
    idxy = getElementSize(id)
    var width = idxy[0],
        height = idxy[1];



    var padding = Math.min( width, height ) * 0.3;


    var innerRadius = Math.min(width-padding, height-padding ) * 0.41,
        outerRadius = innerRadius * 1.1;

    var fill = d3.scale.category10();
        //.domain(d3.range(4))
        //.range(["#000000", "#FFDD89", "#957244", "#F26223"]);

    var svg = d3.select(id)//.insert("svg",':first-child')
        .attr("class", 'circos')
        .attr("width", width)
        .attr("height", height)
        .attr('viewBox','0 0 ' + width + ' ' + height)
        .attr('preserveAspectRatio','xMidYMid')        
      .append("g")
        .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

    // Returns an event handler for fading a given chord group.
    function fade(opacity) {
        return function(g, i) {
            svg.selectAll(".chord path")
                .filter(function(d) { return d.source.index != i && d.target.index != i; })
              .transition()
                .style("opacity", opacity);
        }
    }

    svg.append("g").selectAll("path")
        .data(chord.groups)
      .enter().append("path")
        .style("fill", function(d) { return fill(d.index); })
        .style("stroke", function(d) { return fill(d.index); })
        .attr("d", d3.svg.arc().innerRadius(innerRadius).outerRadius(outerRadius))
        .on("mouseover", fade(0.1))
        .on("mouseout", fade(1));

    var g = svg.append("g").selectAll("g")
        .data(chord.groups)
        .enter().append("g")
        .attr("class", "group");
  
    g.append("path")
        .style("fill", function(d) { return fill(d.index); })
        .attr("d", d3.svg.arc().innerRadius(innerRadius).outerRadius(outerRadius))
        .on("mouseover", fade(0.1))
        .on("mouseout", fade(1));

    g.append("text")
        .each(function(d) { d.angle = (d.startAngle + d.endAngle) / 2; })
        .attr("dy", ".35em")
        .attr("text-anchor", function(d) {
          return d.angle > Math.PI ? "end" : null;
        })
        .attr("transform", function(d) {
          return "rotate(" + (d.angle * 180 / Math.PI - 90) + ")"
              + "translate(" + (innerRadius + 32) + ")"
              + (d.angle > Math.PI ? "rotate(180)" : "");
        })
        .text(function(d) { return labels[d.index]; })
        .attr('style','cursor:pointer;')
        .on("click",function(d){ delegateLink('metapath://db/pathway/'+labels[d.index]+'/view'); });


    svg.append("g")
        .attr("class", "chord")
      .selectAll("path")
        .data(chord.chords)
      .enter().append("path")
        .attr("d", d3.svg.chord().radius(innerRadius))
        .style("fill", function(d) { return fill(d.target.index); })
        .style("opacity", 1);


}


/*

LINE plot 

*/


function lineplot(id, data, identities, labels) {

idxy = getElementSize(id)
var width = idxy[0],
    height = idxy[1];
    

var margin = {top: 120, right: 50, bottom: 80, left: 50};
    //width = width - margin.left - margin.right,
    //height = height - margin.top - margin.bottom;
var width_d = width - margin.left - margin.right,
    height_d = height - margin.top - margin.bottom;
    
var s_x = d3.extent(data, function(d) { return d.x; } )

var s_y = [
    d3.min(data, function(d) { return Math.min.apply(Math, Object.keys(d.y).map(function(key){ return d.y[key]; }) ); } ),
    d3.max(data, function(d) { return Math.max.apply(Math, Object.keys(d.y).map(function(key){ return d.y[key]; }) ); } ),
  ];
                 
var x = d3.scale
            .linear()
            .range([0,width_d])
            .domain( s_x);
            
            
var y = d3.scale
            .linear()
            .range([height_d,0])
            .domain( s_y);
            
/*var zoom = d3.behavior.zoom()
    .x(x)
    //.y(y)
    .on("zoom", zoomed);            */

var color = d3.scale.category10();

var xAxis = d3.svg.axis()
    .scale(x)
    .orient("bottom");

var yAxis = d3.svg.axis()
    .scale(y)
    .orient("left");

var line = d3.svg.line()
    //.interpolate("basis")
    .x(function(d) { return x(d.x); })
    .y(function(d) { return y(d.y); });
    

var svg = d3.select(id)//.insert("svg",':first-child')
    .attr("width", width)
    .attr("height", height)
    .attr('viewBox','0 0 ' + width + ' ' + height)
    .attr('preserveAspectRatio','xMidYMid')
    //  .call(zoom)

    .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")")

    color.domain( d3.keys( data[0].y ) );


  svg.append("g")
      .attr("class", "x axis")
      .attr("transform", "translate(0," + height_d + ")")
      .call(xAxis)
    .append("text")
      .attr("y", 6)
      .attr("dy", ".71em")
      .style("text-anchor", "end")
      .text('ppm');

  svg.append("g")
      .attr("class", "y axis")
      .call(yAxis)
    .append("text")
      .attr("transform", "rotate(-90)")
      .attr("y", 6)
      .attr("dy", ".71em")
      .style("text-anchor", "end")
      .text('Rel');
      
      
var clip = svg.append("svg:clipPath")
    .attr("id", "clip")
    .append("svg:rect")
    .attr("x", 0)
    .attr("y", 0)
    .attr("width", width - (margin.left + margin.right))
    .attr("height", height);


  var plotline = color.domain().map(function(name) {
    return {
      name: name,
      values: data.map(function(d) {
        return {x: d.x, y: +d.y[name]};
      })
    };
  });

  var aline = svg.selectAll(".line")
      .data(plotline)
      
    .enter().append("g")
      .attr("clip-path", "url(#clip)")
      .attr("class", "line");
    
  aline.append("path")
      .attr("class", "line")
      .attr("d", function(d) { return line(d.values); })
      .style("stroke", function(d) { return color(d.name); });


    var rect = {
        'x':(function(d) { return x(d.x); }),
        'y':(function(d) { return y(s_y[1]); }),
        'width':(function(d) { return x( d.x_end) - x(d.x); }),
        'height':(function(d) { return y( 0) - y(s_y[1]); }),
        }
        
    var label_position_transform = function(d,i){ return "translate(" +  x( (d.x+d.x_end)/2 )  +"," + y( s_y[1] )+ ") rotate(-60)"; }

    var identity = svg.selectAll(".identity")
          .data(identities)
          .enter();
          
        identity.append("svg:rect")
                .attr("x", rect.x)
                .attr("y", rect.y)
                .attr("width", rect.width)
                .attr("height", rect.height)
                .attr("class","identity-line")

        identity.append("text")
            .attr("transform", label_position_transform)
                .style("text-anchor", "start")
                .attr("dx", ".1em")     
                .attr("class","identity-label")
          .text(function(d,i) { return d.entity.name; })
            .attr('style','cursor:pointer;')
            .on("click",function(d){ delegateLink( d.entity.url); });          
            
    // Labels         
            
    var label = svg.selectAll(".labels")
          .data(labels)
          .enter();
          
        label.append("svg:rect")
                .attr("x", rect.x)
                .attr("y", rect.y)
                .attr("width", rect.width)
                .attr("height", rect.height)
            .attr("class","label-line");

        label.append("text")
            .attr("transform", label_position_transform)
                .style("text-anchor", "start")
                .attr("dx", ".1em")     
                .attr("class","label-label")
            
          .text(function(d){ return d.label; });
    


}




/*

NMR SPECTRA plot
Specific line plot for NMR spectra vis

*/

function nmr_spectra(id, data, identities, labels) {

idxy = getElementSize(id)
var width = idxy[0],
    height = idxy[1];
    

var margin = {top: 120, right: 50, bottom: 80, left: 50};
    //width = width - margin.left - margin.right,
    //height = height - margin.top - margin.bottom;
var width_d = width - margin.left - margin.right,
    height_d = height - margin.top - margin.bottom;
    
var s_ppm = d3.extent(data, function(d) { return d.ppm; } )
var s_ppm = [ s_ppm[1], s_ppm[0] ]

var s_intensity = [
        d3.min(data, function(d) { var values = Object.keys(d.intensity).map(function(key){ return d.intensity[key]; }); return d3.min(values); } ), 
        d3.max(data, function(d) { var values = Object.keys(d.intensity).map(function(key){ return d.intensity[key]; }); return d3.max(values); } ),
        ]

console.log(s_intensity);
        
var x = d3.scale
            .linear()
            .range([0,width_d])
            .domain( s_ppm);
            
            
var y = d3.scale
            .linear()
            .range([height_d,0])
            .domain( s_intensity);
            
var zoom = d3.behavior.zoom()
    .x(x)
    //.y(y)
    .on("zoom", zoomed);            

var color = d3.scale.category10();

var xAxis = d3.svg.axis()
    .scale(x)
    .orient("bottom");

var yAxis = d3.svg.axis()
    .scale(y)
    .orient("left");

var line = d3.svg.line()
    //.interpolate("basis")
    .x(function(d) { return x(d.ppm); })
    .y(function(d) { return y(d.intensity); });
    

var svg = d3.select(id)//.insert("svg",':first-child')
    .attr("width", width)
    .attr("height", height)
    .attr('viewBox','0 0 ' + width + ' ' + height)
    .attr('preserveAspectRatio','xMidYMid')
    //  .call(zoom)

    .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")")

    color.domain( d3.keys( data[0].intensity ) );


  svg.append("g")
      .attr("class", "x axis")
      .attr("transform", "translate(0," + height_d + ")")
      .call(xAxis)
    .append("text")
      .attr("y", 6)
      .attr("dy", ".71em")
      .style("text-anchor", "end")
      .text('ppm');

  svg.append("g")
      .attr("class", "y axis")
      .call(yAxis)
    .append("text")
      .attr("transform", "rotate(-90)")
      .attr("y", 6)
      .attr("dy", ".71em")
      .style("text-anchor", "end")
      .text('Rel');
      
      
var clip = svg.append("svg:clipPath")
    .attr("id", "clip")
    .append("svg:rect")
    .attr("x", 0)
    .attr("y", 0)
    .attr("width", width - (margin.left + margin.right))
    .attr("height", height);


  var spectra = color.domain().map(function(name) {
    return {
      name: name,
      values: data.map(function(d) {
        return {ppm: d.ppm, intensity: +d.intensity[name]};
      })
    };
  });

  var spectrum = svg.selectAll(".spectrum")
      .data(spectra)
      
    .enter().append("g")
      .attr("clip-path", "url(#clip)")
      .attr("class", "spectrum");
    
  spectrum.append("path")
      .attr("class", "line")
      .attr("d", function(d) { return line(d.values); })
      .style("stroke", function(d) { return color(d.name); });


    var rect = {
        'x':(function(d) { return x(d.ppm); }),
        'y':(function(d) { return y(s_intensity[1]); }),
        'width':(function(d) { return x( d.ppm_end) - x(d.ppm); }),
        'height':(function(d) { return y( 0) - y(s_intensity[1]); }),
        }
        
    var label_position_transform = function(d,i){ return "translate(" +  x( (d.ppm+d.ppm_end)/2 )  +"," + y( s_intensity[1] )+ ") rotate(-60)"; }

    var identity = svg.selectAll(".identity")
          .data(identities)
          .enter();
          
        identity.append("svg:rect")
                .attr("x", rect.x)
                .attr("y", rect.y)
                .attr("width", rect.width)
                .attr("height", rect.height)
                .attr("class","identity-line")

        identity.append("text")
            .attr("transform", label_position_transform)
                .style("text-anchor", "start")
                .attr("dx", ".1em")     
                .attr("class","identity-label")
          .text(function(d,i) { return d.compound.name; })
            .attr('style','cursor:pointer;')
            .on("click",function(d){ delegateLink( d.compound.url); });          
            
    // Labels         
            
    var label = svg.selectAll(".labels")
          .data(labels)
          .enter();
          
        label.append("svg:rect")
                .attr("x", rect.x)
                .attr("y", rect.y)
                .attr("width", rect.width)
                .attr("height", rect.height)
            .attr("class","label-line");

        label.append("text")
            .attr("transform", label_position_transform)
                .style("text-anchor", "start")
                .attr("dx", ".1em")     
                .attr("class","label-label")
            
          .text(function(d){ return d.label; });
    

    function zoomed() {
        svg.select(".x.axis").call(xAxis);
        svg.select(".y.axis").call(yAxis);

        svg.selectAll(".line")
              .attr("class", "line")
              .attr("d", function(d) { return line(d.values); })
              .style("stroke", function(d) { return color(d.name); });

        svg.selectAll(".identity-line")
                .attr("x", rect.x)
                .attr("y", rect.y)
                .attr("width", rect.width)
                .attr("height", rect.height)

        svg.selectAll(".identity-label")
            .attr("transform", label_position_transform)

        svg.selectAll(".label-line")
                .attr("x", rect.x)
                .attr("y", rect.y)
                .attr("width", rect.width)
                .attr("height", rect.height)

        svg.selectAll(".label-label")
            .attr("transform", label_position_transform)

            
    }

}





// Scatter plot
function scatter(id, data, regions, x_axis_label, y_axis_label) {

    idxy = getElementSize(id)
    var width = idxy[0],
        height = idxy[1];
    
    var size = Math.min( width, height );
    
    var margin = {top: 50, right: 50, bottom: 100, left: 100};
        //width = width - margin.left - margin.right,
        //height = height - margin.top - margin.bottom;
    var width_d = size - margin.left - margin.right,
        height_d = size - margin.top - margin.bottom;
        
        
    xmin = d3.min(data, function(d) { return d.x; });
    xmax = d3.max(data, function(d) { return d.x; });

    ymax = d3.max(data, function(d) { return d.y; });
    ymin = d3.min(data, function(d) { return d.y; });
    
            
    var x = d3.scale.linear()
              .domain([xmin, xmax])
              .range([ 0, width_d ]);
    
    var y = d3.scale.linear()
    	      .domain([ymin, ymax])
    	      .range([ height_d, 0 ]);
    	      
    var classes = Array()
    data.forEach( function(d){ classes.push( d.class ) } );
    var classes = d3.unique( classes ); //.keys();

    var color = d3.scale.category10();
        color.domain( classes );    	      

 
    var svg = d3.select(id)//.insert("svg",':first-child')
        .attr('width', width)
        .attr('height', height)
        .attr("viewBox", "0 0 " + width + " " + height  )
        
        .attr('class', 'chart')
        
    var clip = svg.append("svg:clipPath")
        .attr("id", "clip")
        .append("svg:rect")
        .attr("x", 0)
        .attr("y", 0)
        .attr("width", width_d)
        .attr("height", height_d);        

    var main = svg.append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')')
        .attr('width', width_d)
        .attr('height', height_d)
        .attr('class', 'main')   
        
    // draw the x axis
    var xAxis = d3.svg.axis()
        .scale(x)
        .orient('bottom');

    main.append('g')
        .attr('transform', 'translate(0,' + height_d + ')')
        .attr('class', 'main axis date')
        .call(xAxis)
            .append("text")
            .attr("class", "label")
            .attr("x", width_d)
            .attr("y", -6)
            .style("text-anchor", "end")
            .text(x_axis_label);

    // draw the y axis
    var yAxis = d3.svg.axis()
        .scale(y)
        .orient('left');

    main.append('g')
        .attr('transform', 'translate( 0,0)')
        .attr('class', 'main axis date')
        .call(yAxis)
            .append("text")
            .attr("class", "label")
            .attr("transform", "rotate(-90)")
            .attr("y", 6)
            .attr("dy", ".71em")
            .style("text-anchor", "end")
            .text(y_axis_label);

    var g = main.append("svg:g"); 
    
    g.selectAll(".scatter-dots")
        .data(data)
        .enter().append("svg:circle")
            .attr("cx", function (d,i) { return x(d.x); } )
            .attr("cy", function (d) { return y(d.y); } )
            .attr("r", 4)
            .style("fill", function(d) { return color(d.class); })
            .attr("data-legend",function(d) { return d.class; });

    var g = main.append("svg:g")
              .attr("clip-path", "url(#clip)");

    g.selectAll(".region")
        .data(regions)
        .enter().append("svg:ellipse")
            .attr("class", "region")
            .attr("cx", function (d) { return x(d.cx); } )
            .attr("cy", function (d) { return y(d.cy); } )
            .attr("rx", function (d) { return x(d.rx)-x(0); })
            .attr("ry", function (d) { return y(0)-y(d.ry); })
            .style("stroke", function(d) { return color(d.class); });

	// add legend   
	var legend = svg.append("g")
	  .attr("class", "legend")
        //.attr("x", w - 65)
        //.attr("y", 50)
	  .attr("height", 100)
	  .attr("width", 100)
    .attr('transform', 'translate(-20,50)')    
      
    
    legend.selectAll('rect')
      .data(classes)
      .enter()
      .append("rect")
	  .attr("x", width_d+margin.left+margin.right)
      .attr("y", function(d, i){ return i *  15;})
	  .attr("width", 10)
	  .attr("height", 10)
	  .style("fill", function(d) { return color(d); })
      
    legend.selectAll('text')
      .data(classes)
      .enter()
      .append("text")
	  .attr("x", width_d+margin.left+margin.right + 12)
      .attr("y", function(d, i){ return i *  15 + 9;})
	  .text(function(d) { return d; });
  
  
    g.append("line")
            .attr(
            {
                "x1" : x(0),
                "x2" : x(0),
                "y1" : y(ymin),
                "y2" : y(ymax),
                "class":'zerogrid',
            });
    g.append("line")
            .attr(
            {
                "x1" : x(xmin),
                "x2" : x(xmax),
                "y1" : y(0),
                "y2" : y(0),
                "class":'zerogrid',
            });
      
}

