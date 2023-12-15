// ################# LAYOUT WIDGETS #############
const GRID_BOX_COLOR = '#636363'
function modify_grid(){
  layout = document.getElementById('plotly_fig').layout
  xaxis=layout['xaxis']

  let grid_box = {
    linecolor: GRID_BOX_COLOR,
    linewidth: 6
  }

  xaxis['showgrid'] = document.getElementById('grid_x').checked
  xaxis['showline'] = true
  xaxis['mirror']= 'ticks'
  xaxis['gridcolor']= '#bdbdbd'
  xaxis['gridwidth']= 2

  let yaxis = {
    showgrid: document.getElementById('grid_y').checked,
    zeroline: document.getElementById('zeroline').checked,
    showline: true,
    mirror: 'ticks',
    gridcolor: '#bdbdbd',
    gridwidth: 2,
    zerolinecolor: '#969696',
    zerolinewidth: 4,
    }
  if (document.getElementById('grid_box').checked){
    xaxis = Object.assign({}, xaxis, grid_box);
    yaxis = Object.assign({}, yaxis, grid_box);
  }
  layout = {
    xaxis:xaxis,
    // yaxis:yaxis
  }
  Plotly.relayout('plotly_fig', layout)
}

function update_ticks(){
  nticks = parseInt(document.getElementById('in_nticks').value)
  for (ax of Object.keys(fig.layout).filter(x=>x.includes('yaxis'))){
    r = fig['layout'][ax]['range']
    tickvals = linspace(r[0],r[1],nticks)
    ticktext = tickvals.map(x=>formatNumber(x))
    update = {}
    update[ax+'.tickvals'] = tickvals
    update[ax+'.ticktext'] = ticktext
    update[ax+'.tickmode'] = 'array'
    Plotly.relayout('plotly_fig',update)
}
}

function update_size_figure(e){
layout = fig.layout
if (e.id == 'btn_width'){
  layout['width'] = e.value
}else if (e.id == 'btn_height') {
  layout['height'] = e.value
}
Plotly.relayout('plotly_fig', layout)
}
function change_color_paper_background(color){
  Plotly.relayout('plotly_fig', {'paper_bgcolor':color});
}

// #################################################
function get_std_axis(){
  // ax_col = GRID_BOX_COLOR
  ax_col = 'red'
  gw = 2
  grid_color='#bdbdbd'
  fs = 12
  return {
      linecolor: ax_col,
      linewidth: 4,
      ticks: 'outside',
      tickfont: {'color':ax_col},
      ticklen: 8,
      title: {
      font: {color: ax_col,
          size:fs,
          family:"Times New Roman"
      },
      standoff:0,
      },
      tickwidth:2,
      tickcolor:ax_col,
      gridcolor : grid_color,
      zeroline : false,
      gridwidth : gw,
      anchor:'free'
  }
}

function load_planche(){
  file = fileInput.files[0];
  console.log(file);
  JSON_READER.readAsText(file);
}


// const JSON_READER = new FileReader();
// JSON_READER.onload = function(event) {
//   try {
//     const data = JSON.parse(event.target.result);
//     // console.log('JSON content:', data);
//     empty_table_traces()
//     for (tag_name in data){
//       row = data[tag_name]
//       add_row_trace_table(tag_name,row['color'],row['unit'],row['row_id'],row['col_id']);
//     }
//   } catch (error) {
//     console.error('Error parsing JSON:', error);
//   }
// };

function get_table_traces_json(){
  table_tags_dict = {}
  for (row of Array.from(table_traces.children[0].children).slice(1,)){
      table_tags_dict[row.children[0].textContent]={
      label : row.children[5].children[0].value,
      color : row.children[1].textContent,
      unit :  row.children[2].children[0].value,
      row_id : row.children[3].children[0].value,
      col_id : row.children[4].children[0].value,
      // size_mult : row.children[5].children[0].value,
      }
  }
  return table_tags_dict
}

function save_planche(){
  const blob = new Blob([JSON.stringify(get_table_traces_json())], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'planche.json';
  a.click();
  URL.revokeObjectURL(url);
}

function browseForPlanche() {
  fileInput.click();
}



function add_row_trace_table(tag_name,color,unit,row_id,col_id){
  var row = table_traces.insertRow(table_traces.rows.length);
  row.insertCell(0).innerHTML = tag_name

  color_but = document.createElement('button')
  color_but.style.backgroundColor = color
  color_but.textContent = color
  color_but.id = 'color_d_' + tag_name
  color_but.classList.add('color_button')
  color_but.addEventListener('click', function (e) {popup_trace_color_picker(e.target)})
  row.insertCell(1).append(color_but)

  unit_in = document.createElement('input')
  unit_in.value = unit
  unit_in.classList.add('table_input')
  row.insertCell(2).append(unit_in)

  row_in = document.createElement('input')
  row_in.type='number'
  row_in.min=1
  row_in.max=10
  row_in.value=row_id
  row_in.step=1
  row_in.classList.add('table_input')
  row_in.addEventListener('change', function (e) {repositon_trace_layout(e.target.parentElement)})
  row.insertCell(3).append(row_in)

  col_in = document.createElement('input')
  col_in.type='number'
  col_in.min=1
  col_in.max=10
  col_in.value=col_id
  col_in.step=1
  col_in.classList.add('table_input')
  col_in.addEventListener('change', function (e) {repositon_trace_layout(e.target.parentElement)})
  row.insertCell(4).append(col_in)

  size_in = document.createElement('input')
  size_in.type='number'
  size_in.min=0.1
  size_in.max=10
  size_in.value=1
  size_in.step=0.01
  size_in.classList.add('table_input')
  size_in.addEventListener('change', function (e) {
      cur_tag = e.target.parentElement.parentElement.children[0].textContent
      trace_id = Array.from(plotly_fig.data).map(x=>x.tag).indexOf(cur_tag)
      Plotly.restyle(plotly_fig,{"marker.size":parseInt(marker_size.value)*parseInt(e.target.value)},trace_id)
  });
  // row.insertCell(5).append(size_in)

  label_in = document.createElement('input')
  label_in.classList.add('table_input')
  label_in.value = tag_name
  label_in.style.width = '150px'
  label_in.addEventListener('change', function (e) {
      cur_tag = e.target.parentElement.parentElement.children[0].textContent
      trace_id = Array.from(plotly_fig.data).map(x=>x.tag).indexOf(cur_tag)
      Plotly.restyle(plotly_fig,{name:e.target.value},trace_id)
  });
  row.insertCell(5).append(label_in)
}

function empty_table_traces(){
  nbrows = table_traces.rows.length
  for (let index=1;index<nbrows;index++){
    table_traces.deleteRow(1)
  }
}

function update_table_traces() {
  empty_table_traces()
  for (trace of plotly_fig.data){
      add_row_trace_table(trace.name,trace.marker.color,trace.customdata[0],1,1)
  }
}



function create_x_axis(xax_name){
xax = get_std_axis()
xax['type'] = 'date'
xax['title']['text'] = xax_name
layout = {}
layout[xax_name] = xax
Plotly.relayout('plotly_fig',layout)
}

function create_y_axis(yax_name,unit){
yax = get_std_axis()
yaxtext = 'y' + yax_name.slice(5,) +  ' : ' + unit
// yaxtext = unit
yax['title']['text'] = yaxtext
yax['unit'] = unit
layout = {}
layout[yax_name] = yax
Plotly.relayout('plotly_fig',layout)
}

function delete_unused_axes(){
return new Promise(function(resolve, reject) {
  y_axes_data = fig.data.map(x=>x.yaxis)
  layout = fig.layout
  y_axis_layout = Array.from(Object.keys(fig.layout)).filter(y=>y.includes('yaxis'))
  for (y of y_axis_layout){
    if(!(y_axes_data.includes('y' + y.slice(5,)))){
      // console.log(y + 'unused. Being deleted.');
      delete layout[y]
    }
  }
  Plotly.relayout('plotly_fig',layout)
  .then(()=>{
    resolve()
  })
});
}

function redefine_y_domains_of_col(col){
  sy = parseFloat(in_sy.value)
  return new Promise(function(resolve, reject) {
    lay = {}
    fig_subplots = Array.from(Object.keys(fig.layout)).filter(x=>x.includes('yaxis')).map(x=>x.slice(5,x.length-1))
    rows = fig_subplots.map(x=>parseInt(x[0]))
    nb_rows = Math.max(...rows)
    new_domains = divide_interval(nb_rows,sy,1)
    for (i=1;i<=new_domains.length;i++){
      lay['yaxis' + i + col + '1.domain'] = new_domains[i-1]
    }
    Plotly.relayout('plotly_fig',lay)
    .then(()=>{
      resolve()
    })
  })
}

function redefine_x_domains_of_row(row){
return new Promise(function(resolve, reject) {
  lay = {}
  sx = parseFloat(in_sx.value)
  max_x = 0.97
  // console.log('current row:' + row);
  row = 1
  fig_subplots = Array.from(Object.keys(fig.layout)).filter(x=>x.includes('yaxis')).map(x=>x.slice(5,x.length-1))
  cols = fig_subplots.map(x=>parseInt(x[1]))
  nb_cols = Math.max(...cols)
  new_domains = divide_interval(nb_cols,sx,max_x)
  for (j=1;j<=new_domains.length;j++){
    jj=j
    if (jj==1){jj=''}
    lay['xaxis' + jj +'.domain'] = new_domains[j-1]
  }
  Plotly.relayout('plotly_fig',lay)
  .then(()=>{
    console.log('redifintion of axes domains are done');
    resolve()
  })
})
}

function repositon_trace_layout(e){
  tag = e.parentElement.children[0].textContent
  console.log(tag);

  var table_tags_dict = get_table_traces_json()
  cur_tag_change = table_tags_dict[tag]
  // get the new subplot on which the trace should be
  sp = cur_tag_change.row_id + cur_tag_change.col_id

  // get all the existing fig_subplots
  fig_subplots = Array.from(Object.keys(fig.layout)).filter(x=>x.includes('yaxis')).map(x=>x.slice(5,x.length-1))
  trace_id = Array.from(fig.data).map(x=>x.name).indexOf(cur_tag_change.label)
  xn = sp[1]
  if (xn=='1'){xn=''}
  xax_name = 'xaxis' + xn
  var yax_name
  // should a subplot be created ?
  if (!fig_subplots.includes(sp)){
    console.log('a subplot should be created :sp' +sp);
    // should an x-axis be added ?
    cols = fig_subplots.map(x=>parseInt(x[1]))
    if ( !cols.includes(parseInt(sp[1])) && (sp[1]!='1')){
      console.log('an x-axis should be created');
      create_x_axis(xax_name)
    }else{
      console.log('no x-axis creation==>cols : ',cols);
    }
    // a y-axis must be added
    yax_name = 'yaxis' + sp + 1
    create_y_axis(yax_name,cur_tag_change.unit)
  }
  else{
    console.log('no need to create subplot ');
    list_y_axes = Array.from(Object.keys(fig.layout)).filter(x=>x.includes('yaxis' + sp[0] + sp[1]))
    y_units = {}
    for (yy of list_y_axes){
      y_units[fig.layout[yy].unit] = yy
    }
    yax_name = y_units[cur_tag_change.unit]
    // should a y-axis be overlaid ?
    if (!yax_name){
      nb_over = Math.max(...list_y_axes.map(x=>parseInt(x.slice(-1))))+1
      yax_nb = sp + nb_over
      yax_name = 'yaxis' + yax_nb
      console.log('new y-axis '+ yax_name +' overlaying on y' + sp);
      create_y_axis(yax_name,cur_tag_change.unit)
      layout = {}
      layout[yax_name+'.overlaying'] ='y' + sp + 1
      Plotly.relayout('plotly_fig',layout)
    }else {
      console.log('no need to add a y-axis');
    }
  }
  // position the trace on the currect axis
  console.log(xax_name);
  Plotly.restyle('plotly_fig',{'xaxis':'x' + xax_name.slice(5,),yaxis:'y' + yax_name.slice(5,)},trace_id)
  .then(()=>{
    // relayout the existing x-axis domains
    delete_unused_axes()
    .then(()=>{
      redefine_x_domains_of_row(sp[0])
      .then(()=>{
        redefine_y_domains_of_col(sp[1])
        .then(()=>{
          reposition_yaxes()
          update_ticks()
        })
      })
    })
  })
}

////fake just to reload quickly the figure
function load_planche(){
  file = fileInput.files[0];
  jsonread = new FileReader();
  jsonread.onload = function(event) {
    try {
      fig = JSON.parse(event.target.result);
      Plotly.newPlot('plotly_fig',fig.data,fig.layout,CONFIG).then(()=>{
        update_table_traces()
      })
    }catch (error) {
      console.error('Error loading_figure:', error);
    }
  };
  jsonread.readAsText(file)
}

function reposition_yaxis(yax_name){
  lay = {}
  shift = parseFloat(in_sa.value)
  //find x axis
  x_ax=yax_name.slice(6,7)
  if (x_ax=='1'){x_ax=''}
  x_ax = 'xaxis'+x_ax
  //find overlay index
  k = yax_name.slice(7,8)
  nb = Math.floor((k-1)/2)
  console.log(yax_name,x_ax,', k:'+k,' nb :'+nb);
  if (k%2==0){
    side ='right'
    position = fig.layout[x_ax].domain[1] + nb*shift
  }else {
    side = 'left'
    position = fig.layout[x_ax].domain[0] - nb*shift
  }
  console.log(yax_name + ':',position, side);
  position = saturates(position,0,1)
  lay[yax_name+'.side'] = side
  lay[yax_name+'.position'] = position
  Plotly.relayout('plotly_fig',lay)
}

function reposition_yaxes(){
  for (ax of Object.keys(fig.layout).filter(x=>x.includes('yaxis'))){
    reposition_yaxis(ax)
  }
}
function update_font_size_axes(){
  fs = parseFloat(in_fs_axes.value)
  for (ax of Object.keys(fig.layout).filter(x=>x.includes('axis'))){
    lay={}
    lay[ax+'.tickfont.size'] = fs 
    lay[ax+'.title.font.size'] = fs*1.2
    Plotly.relayout('plotly_fig',lay)
  }
}


// ################# TRACES WIDGETS #############
function update_size_markers(){
  size = parseInt(document.getElementById('marker_size').value)
  update = {
    'marker.size':size
  }
    Plotly.restyle('plotly_fig', update);
}

// config_colors = get_table_traces_json()
function update_trace_color(tag,color){
  trace_id = fig.data.map(x=>x.tag).indexOf(tag)
  Plotly.restyle('plotly_fig', {'line.color':color,'marker.color':color}, trace_id);
}

function update_style_fig(e) {
  let style=e.value
  let mode
  let line_shape = 'linear'
  if (style=='lines+markers'){mode = 'lines+markers'}
  else if( style=='markers'){mode='markers'}
  else if (style=='lines'){mode='lines'}
  else if (style=='stairs'){
    mode='lines+markers'
    line_shape='hv'
  }
  var update = {
    mode:mode,
    line:{shape:line_shape},
  }
  Plotly.restyle('plotly_fig', update);
}

// #########################################
function change_x_axis(){
  tag_x = document.getElementById('select_dd_x').value
  if (tag_x=='Time'){
    new_x_data = TIMES
    fig.layout['xaxis']['type'] = "date"
  }else {
    cur_trace = fig.data.map(x=>x.name).indexOf(tag_x)
    new_x_data = fig.data[cur_trace].y
    fig.layout['xaxis']['type'] = "number"
  }
  for(k=0;k<fig.data.length;k++){
    fig.data[k].x = new_x_data;
  }
  fig.layout['xaxis']['title']['text'] = tag_x
  // Plotly.update('plotly_fig', fig.data, fig.layout);
  Plotly.update('plotly_fig', fig.data, fig.layout).then(()=>{
      update_hover()
      dd_style = document.getElementById('dd_style')
      if (tag_x=='Time'){
        dd_style.value = "lines+markers"
      }else{
        dd_style.value = 'markers'
        document.getElementById('marker_size').value = "12"
        update_size_markers()
      }
      dd_style.dispatchEvent(new Event("change"));
  })
}
