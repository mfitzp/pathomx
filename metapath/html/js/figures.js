/* Helper functions */
QtViewportSize = typeof(QtViewportSize) == 'undefined' ? {'x':false,'y':false} : QtViewportSize;
nan = null /* For numpy compatibiltiy */
    
    function getWindowSize(){
        var w = window,
            d = document,
            e = d.documentElement,
            g = d.getElementsByTagName('body')[0],
            q = QtViewportSize;
            
            x = q.x || w.innerWidth || e.clientWidth || g.clientWidth,
            y = q.y || w.innerHeight|| e.clientHeight|| g.clientHeight;
    
        return [x,y]
    }
    
    function getElementSize(id){
        if (id == 'body' || id =='svg'){
            return getWindowSize();
        } else {
            xy = [        
                d3.select(id)[0][0].offsetWidth.parseInt(),
                d3.select(id)[0][0].offsetHeight.parseInt(),
                ];
            if (xy[1] == 0) { xy[1] = xy[0]*2/3; } //800*600
            return xy
        }
    }

    
    
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
    
    var x = d3.scale
                .ordinal()
                .domain(xlabels )
                .rangeBands([0, xlabels.length*cellw]),
        y = d3.scale
                .ordinal()
                .domain(ylabels)
                .rangeBands([0, ylabels.length*cellh]),
        z = d3.scale
                .linear()
                .domain( [-r , 0, +r] )
                //.domain( [d3.min(buckets, function(d) { return d.value; }) , 0, d3.max(buckets, function(d) { return d.value; })] )
                .range(["#2166ac","#f7f7f7","#b2182b"]);
                
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


function corrmatrix(id, groups, traits, data){

    idxy = getElementSize(id)
    var width = idxy[0],
        height = idxy[1];

    var size = 140,
          padding = 10,
          n = 4;
          
  // Position scales.
  var x = {}, y = {};
  traits.forEach(function(trait) {
    // Coerce values to numbers.
    data.forEach(function(d) { d[trait] = +d[trait]; });

    var value = function(d) { return d[trait]; },
        domain = [d3.min(data, value), d3.max(data, value)],
        range = [padding / 2, size - padding / 2];
    x[trait] = d3.scale.linear().domain(domain).range(range);
    y[trait] = d3.scale.linear().domain(domain).range(range.reverse());
  });

  // Axes.
  var axis = d3.svg.axis()
      .ticks(5)
      .tickSize(size * n);

  // Brush.
  var brush = d3.svg.brush()
      .on("brushstart", brushstart)
      .on("brush", brush)
      .on("brushend", brushend);
      
      

  // Root panel.
  var svg = d3.select(id)//.insert("svg",':first-child')
        .attr("width", width)
        .attr("height",height)
        .attr('viewBox','0 0 ' + width + ' ' + height)
        .attr('preserveAspectRatio','xMidYMid')        
      
    .append("svg:g")
      .attr("transform", "translate(359.5,69.5)");

  // Legend.
  var legend = svg.selectAll("g.legend")
      .data(["setosa", "versicolor", "virginica"])
    .enter().append("svg:g")
      .attr("class", "legend")
      .attr("transform", function(d, i) { return "translate(-179," + (i * 20 + 594) + ")"; });

  legend.append("svg:circle")
      .attr("class", String)
      .attr("r", 3);

  legend.append("svg:text")
      .attr("x", 12)
      .attr("dy", ".31em")
      .text(function(d) { return "Iris " + d; });

  // X-axis.
  svg.selectAll("g.x.axis")
      .data(traits)
    .enter().append("svg:g")
      .attr("class", "x axis")
      .attr("transform", function(d, i) { return "translate(" + i * size + ",0)"; })
      .each(function(d) { d3.select(this).call(axis.scale(x[d]).orient("bottom")); });

  // Y-axis.
  svg.selectAll("g.y.axis")
      .data(traits)
    .enter().append("svg:g")
      .attr("class", "y axis")
      .attr("transform", function(d, i) { return "translate(0," + i * size + ")"; })
      .each(function(d) { d3.select(this).call(axis.scale(y[d]).orient("right")); });

  // Cell and plot.
  var cell = svg.selectAll("g.cell")
      .data(cross(traits, traits))
    .enter().append("svg:g")
      .attr("class", "cell")
      .attr("transform", function(d) { return "translate(" + d.i * size + "," + d.j * size + ")"; })
      .each(plot);

  // Titles for the diagonal.
  cell.filter(function(d) { return d.i == d.j; }).append("svg:text")
      .attr("x", padding)
      .attr("y", padding)
      .attr("dy", ".71em")
      .text(function(d) { return d.x; });

  function plot(p) {
    var cell = d3.select(this);

    // Plot frame.
    cell.append("svg:rect")
        .attr("class", "frame")
        .attr("x", padding / 2)
        .attr("y", padding / 2)
        .attr("width", size - padding)
        .attr("height", size - padding);

    // Plot dots.
    cell.selectAll("circle")
        .data(data)
      .enter().append("svg:circle")
        .attr("class", function(d) { return d.group; })
        .attr("cx", function(d) { return x[p.x](d[p.x]); })
        .attr("cy", function(d) { return y[p.y](d[p.y]); })
        .attr("r", 3);

    // Plot brush.
    cell.call(brush.x(x[p.x]).y(y[p.y]));
  }

  // Clear the previously-active brush, if any.
  function brushstart(p) {
    if (brush.data !== p) {
      cell.call(brush.clear());
      brush.x(x[p.x]).y(y[p.y]).data = p;
    }
  }

  // Highlight the selected circles.
  function brush(p) {
    var e = brush.extent();
    svg.selectAll(".cell circle").attr("class", function(d) {
      return e[0][0] <= d[p.x] && d[p.x] <= e[1][0]
          && e[0][1] <= d[p.y] && d[p.y] <= e[1][1]
          ? d.group : null;
    });
  }

  // If the brush is empty, select all circles.
  function brushend() {
    if (brush.empty()) svg.selectAll(".cell circle").attr("class", function(d) {
      return d.group;
    });
  }

  function cross(a, b) {
    var c = [], n = a.length, m = b.length, i, j;
    for (i = -1; ++i < n;) for (j = -1; ++j < m;) c.push({x: a[i], i: i, y: b[j], j: j});
    return c;
  }

}


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
        Math.min.apply(null, d3.min(data, function(d) { var values = Object.keys(d.intensity).map(function(key){ return d.intensity[key]; }); return values; } ) ), 
        Math.max.apply(null, d3.max(data, function(d) { var values = Object.keys(d.intensity).map(function(key){ return d.intensity[key]; }); return values; } ) ),
        ]
                    
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
      .call(zoom)

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


/* 

DIFFERENCE CHART
Plot two data lines with differences between each line highlighted in colour

*/


function difference(id, data) {

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
    d3.min(data, function(d) { return Math.min(d.a, d.b); }),
    d3.max(data, function(d) { return Math.max(d.a, d.b); })
  ];

var x = d3.scale
            .linear()
            .range([0,width_d])
            .domain( s_ppm);

            
var y = d3.scale
            .linear()
            .range([height_d,0])
            .domain( s_intensity);
        

var color = d3.scale.category10();

var xAxis = d3.svg.axis()
    .scale(x)
    .orient("bottom");

var yAxis = d3.svg.axis()
    .scale(y)
    .orient("left");

var area = d3.svg.area()
    //.interpolate("basis")
    .x(function(d) { return x(d.ppm); })
    .y(function(d) { return y(d.a); });
    
var line = d3.svg.line()
    //.interpolate("basis")
    .x(function(d) { return x(d.ppm); })
    .y(function(d) { return y(d.b); });
    


var svg = d3.select(id)//.insert("svg",':first-child')
    .attr("width", width)
    .attr("height", height)
    .attr('viewBox','0 0 ' + width + ' ' + height)
    .attr('preserveAspectRatio','xMidYMid')        

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

  svg.datum(data);

  svg.append("clipPath")
      .attr("id", "clip-below")
    .append("path")
      .attr("d", area.y0(height));

  svg.append("clipPath")
      .attr("id", "clip-above")
    .append("path")
      .attr("d", area.y0(0));

  svg.append("path")
      .attr("class", "area above")
      .attr("clip-path", "url(#clip-above)")
      .attr("d", area.y0(function(d) { return y(d.b); }));

  svg.append("path")
      .attr("class", "area below")
      .attr("clip-path", "url(#clip-below)")
      .attr("d", area);

  svg.append("path")
      .attr("class", "line")
      .attr("d", line);

  svg.append("g")
      .attr("class", "x axis")
      .attr("transform", "translate(0," + height + ")")
      .call(xAxis);


}

