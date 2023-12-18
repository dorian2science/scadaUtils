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
  for (ax of Object.keys(plotly_fig.layout).filter(x=>x.includes('yaxis'))){
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
layout = plotly_fig.layout
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
function create_std_axis(){
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
      anchor:'free',
      position:0,
      side:"left"
  }
}



function load_planche(){
  file = fileInput.files[0];
  console.log(file);
  JSON_READER.readAsText(file);
}


const JSON_READER = new FileReader();
JSON_READER.onload = function(event) {
  try {
    const data = JSON.parse(event.target.result);
    // console.log('JSON content:', data);
    empty_table_traces()
    for (tag_name in data){
      row = data[tag_name]
      add_row_trace_table(tag_name,row['color'],row['unit'],row['row_id'],row['col_id']);
    }
  } catch (error) {
    console.error('Error parsing JSON:', error);
  }
};

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
  // row_in.addEventListener('change', function (e) {repositon_trace_layout(e.target.parentElement)})
  row.insertCell(3).append(row_in)

  col_in = document.createElement('input')
  col_in.type='number'
  col_in.min=1
  col_in.max=10
  col_in.value=col_id
  col_in.step=1
  col_in.classList.add('table_input')
  // col_in.addEventListener('change', function (e) {repositon_trace_layout(e.target.parentElement)})
  row.insertCell(4).append(col_in)

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
  return new Promise(function(resolve, reject) {
    empty_table_traces()
    for (trace of plotly_fig.data){
      add_row_trace_table(trace.name,trace.marker.color,trace.unit,1,1)
    }
    resolve()
  });
}

function create_x_axis(xax_name){
xax = create_std_axis()
xax['type'] = 'date'
xax['title']['text'] = xax_name
layout = {}
layout[xax_name] = xax
Plotly.relayout('plotly_fig',layout)
}

function create_y_axis(yax_name,unit){
yax = create_std_axis()
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
  y_axes_data = plotly_fig.data.map(x=>x.yaxis)
  layout = plotly_fig.layout
  y_axis_layout = Array.from(Object.keys(plotly_fig.layout)).filter(y=>y.includes('yaxis'))
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

function redefine_y_domains(){
  sy = parseFloat(in_sy.value)
  return new Promise(function(resolve, reject) {
    lay = {}
    fig_subplots = Array.from(Object.keys(plotly_fig.layout)).filter(x=>x.includes('yaxis')).map(x=>x.slice(5,x.length-1))
    rows = fig_subplots.map(x=>parseInt(x[0]))
    nb_rows = Math.max(...rows)
    new_domains = divide_interval(nb_rows,sy,1)
    nb_cols = Array.from(Object.keys(plotly_fig.layout)).filter(x=>x.includes('xaxis')).length
    for (i=1;i<=new_domains.length;i++){
      for (j=1;j<=nb_cols;j++){
        lay['yaxis' + i + j + '1.domain'] = new_domains[i-1]
      }
    }
    Plotly.relayout('plotly_fig',lay)
    .then(()=>{
      resolve()
    })
  })
}

function redefine_x_domains(){
return new Promise(function(resolve, reject) {
  lay = {}
  sx = parseFloat(in_sx.value)
  max_x = 0.97
  fig_subplots = Array.from(Object.keys(plotly_fig.layout)).filter(x=>x.includes('yaxis')).map(x=>x.slice(5,x.length-1))
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
    reposition_yaxes()
    update_ticks()
    resolve()
  })
})
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
  // console.log(yax_name,x_ax,', k:'+k,' nb :'+nb);
  if (k%2==0){
    side ='right'
    position = plotly_fig.layout[x_ax].domain[1] + nb*shift
  }else {
    side = 'left'
    position = plotly_fig.layout[x_ax].domain[0] - nb*shift
  }
  // console.log(yax_name + ':',position, side);
  position = saturates(position,0,1)
  lay[yax_name+'.side'] = side
  lay[yax_name+'.position'] = position
  Plotly.relayout('plotly_fig',lay)
}

function reposition_yaxes(){
  for (ax of Object.keys(plotly_fig.layout).filter(x=>x.includes('yaxis'))){
    reposition_yaxis(ax)
  }
}

function update_font_size_axes(){
  fs = parseFloat(in_fs_axes.value)
  for (ax of Object.keys(plotly_fig.layout).filter(x=>x.includes('axis'))){
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
  trace_id = plotly_fig.data.map(x=>x.tag).indexOf(tag)
  Plotly.restyle('plotly_fig', {'line.color':color,'marker.color':color}, trace_id).then(()=>update_style_fig());
}

function update_traces_color(){
  dt = get_table_traces_json()
  for (tag in dt){
    update_trace_color(tag,dt[tag]['color'])
  }
}

function update_style_fig() {
  let style=dd_style.value
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
    plotly_fig.layout['xaxis']['type'] = "date"
  }else {
    cur_trace = plotly_fig.data.map(x=>x.name).indexOf(tag_x)
    new_x_data = plotly_fig.data[cur_trace].y
    plotly_fig.layout['xaxis']['type'] = "number"
  }
  for(k=0;k<plotly_fig.data.length;k++){
    plotly_fig.data[k].x = new_x_data;
  }
  plotly_fig.layout['xaxis']['title']['text'] = tag_x
  // Plotly.update('plotly_fig', plotly_fig.data, plotly_fig.layout);
  Plotly.update('plotly_fig', plotly_fig.data, plotly_fig.layout).then(()=>{
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

function update_hover(){
  TIMES = DATA['Time']
  fig = document.getElementById('plotly_fig')
  text_date = TIMES.map(k=>formatDateTime(new Date(k)))
  precision = parseInt(document.getElementById('n_digits').value)
  tag_x = document.getElementById('select_dd_x').value
  
  for (k=0;k<plotly_fig.data.length;k++){
    trace = plotly_fig.data[k]
    units = Array(trace['y'].length).fill(trace.unit)
    update={
      customdata:[units],
      hovertemplate : '<i>value</i>: %{y:.'+precision+'f} %{customdata}<br>'+'<b>%{text}' + '<br>',
      text:[text_date],
      hoverlabel:{
        font:{size:parseInt(document.getElementById('fs_hover').value)},
        font_family:"Arial"
      }
    }
    if (tag_x !='Time'){
      update['hovertemplate']= update['hovertemplate'] + tag_x +'</b> : %{x}'
    }
    Plotly.restyle('plotly_fig', update,k)
  }
}

function transform_2_std_axis(yaxis_name){
  // ax_col = GRID_BOX_COLOR
  ax_col = 'red'
  gw = 2
  grid_color='#bdbdbd'
  fs = 12
  update={}
  update[yaxis_name + '.' +'linecolor']= ax_col
  update[yaxis_name + '.' +'linewidth']= 4
  update[yaxis_name + '.' +'ticks']= 'outside'
  update[yaxis_name + '.' +'tickfont']= {'color':ax_col}
  update[yaxis_name + '.' +'ticklen']= 8
  update[yaxis_name + '.' +'font.color']= ax_col
  update[yaxis_name + '.' +'tickwidth']=2
  update[yaxis_name + '.' +'tickcolor']=ax_col
  update[yaxis_name + '.' +'gridcolor']= grid_color
  update[yaxis_name + '.' +'zeroline']= false
  update[yaxis_name + '.' +'gridwidth']= gw
  update[yaxis_name + '.' +'anchor'] ='free'
Plotly.relayout('plotly_fig',update)
}

function build_layout_from_planch(){
  // build the layout
  var table_tags_dict = get_table_traces_json()
  cols = Array.from(Object.values(table_tags_dict)).map(v => parseInt(v.col_id))
  nb_cols = Math.max(...cols)
  rows = Array.from(Object.values(table_tags_dict)).map(v => parseInt(v.row_id))
  nb_rows = Math.max(...rows)
  
  x_domains = divide_interval(nb_cols,parseFloat(in_sx.value),1)
  y_domains = divide_interval(nb_rows,parseFloat(in_sy.value),1)

  layout = {}

  for (j=1;j<=nb_cols;j++){
    // create the x-axes
    xax = create_std_axis()
    xax['domain'] = x_domains[j-1]
    xax['type'] = 'date'
    ax_idx = j
    if (ax_idx==1){
      ax_idx = ''
    }
    xax_name = 'xaxis' + ax_idx
    xax['title'].text = xax_name
    layout[xax_name] = xax

    for (i=1;i<=nb_rows;i++){
      sp = i.toString() + j.toString()
      first_yaxis_name = 'yaxis' + sp + 1 
      first_y_name = 'y' + sp + 1

      // determine the number of axes on that subplot
      units_sp = Object.values(table_tags_dict).filter(x=>(x.col_id==j) &&(x.row_id==i)).map(x=>x.unit)
      units_sp = Array.from(new Set(units_sp));
      // console.log(units_sp);

      yax = create_std_axis()
      yax['domain'] = y_domains[i-1]
      yax['position'] = 0
      yax['title'].text = first_y_name +':'+ units_sp[0]
      yax['unit'] = units_sp[0]
      layout[first_yaxis_name] = yax
      
      // put the others axes/units
      for (k=1;k<units_sp.length;k++){
        yax = create_std_axis()
        yax['overlaying'] = first_y_name
        yax['unit'] = units_sp[k]
        yax['title'].text = 'y' + sp + (k+1) + ':'+ units_sp[k]
        layout['yaxis' + sp + (k+1)] = yax
      }
    }
  }

  layout


  data = []
  tags = Object.keys(table_tags_dict)
  list_yaxes=Object.keys(layout).filter(x=>x.includes('yaxis'))
  for (k=0;k<tags.length;k++){
    tag = tags[k]
    trace = table_tags_dict[tag]
    sp = trace.row_id + trace.col_id 
    list_sp_axes = list_yaxes.filter(x=>x.includes('yaxis'+sp))
    ax_nb = list_sp_axes.map(x=>layout[x].unit).indexOf(trace.unit)+1
    old_trace = plotly_fig.data.filter(x=>x.tag==tag)[0]
    new_trace = {
      x : old_trace['x'],
      y : old_trace['y'],
      xaxis : 'x'+sp[1],
      yaxis : 'y'+ sp + ax_nb,
      marker : {"color":trace['color']},
      line : {"color":trace['color']},
      tag : tag,
      name : trace['label'],
      type : 'scattergl',
      unit : trace.unit,
    }
    data.push(new_trace)
  }

  Plotly.newPlot('plotly_fig',data,layout,CONFIG)
  .then(()=>{
    update_style_fig()
    update_hover()
    reposition_yaxes()
    update_ticks()
  })
}
