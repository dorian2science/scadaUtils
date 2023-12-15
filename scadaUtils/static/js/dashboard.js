// ########################
// #      FUNCTIONS       #
// ########################
function update_legend() {
  // let mode = Array.from($('input[type=radio][name=legend]')).filter(x=>x.checked)[0].value
  // // console.log(mode)
  // if (mode=='unvisible') {
  //   Plotly.restyle('plotly_fig', {'showlegend': false});
  // } else {
  //   Plotly.restyle('plotly_fig', {'showlegend': true})
  //   let tags=Array.from($('.legendtext')).map(x=>x.dataset.unformatted)
  //   $.post('/send_description_names',JSON.stringify({mode:mode,tags:tags}),function(data,status){
  //     console.log(data);
  //     // let new_names=JSON.parse(data)
  //     // new_names=Object.values(new_names)
  //     // console.log(new_names);
  //     update={
  //       'name':Object.values(data),
  //       'showlegend': true
  //     }
  //     Plotly.restyle('plotly_fig', update);
  //   })
  // }
}

function update_size_markers(){
  size = parseInt(document.getElementById('marker_size').value)
  update = {
    'marker.size':size
  }
    Plotly.restyle('plotly_fig', update);
}

function update_colors_figure(e) {
  if (e.checked) {
    colors = LIST_DISTINCT_COLORS
    old_colors = document.getElementById('plotly_fig')['data'].map(x => x['marker']['color'])
    LIST_ORIGINAL_COLORS = old_colors
  }else{
    colors = LIST_ORIGINAL_COLORS
  }

  update = {
    'line.color':colors,
    'marker.color':colors,
  }
  Plotly.restyle('plotly_fig', update);
}

function data2excel(){
  let fig=document.getElementById('plotly_fig')
  $.post('/export2excel',JSON.stringify({data:fig.data,layout:fig.layout}),function(res,status){
    var status=res['status']
    if( status=='ok') {
      console.log(res['filename'])
      window.open(res['filename'])
    }else {
      alert(res['notif'])
    }
  })
}


function export_figure(){
  figure = {
    data: fig.data,
    layout: fig.layout,
    config: fig.config
  };
  const figureJSON = JSON.stringify(figure);
  const blob = new Blob([`<!DOCTYPE html><html><head><script src="https://cdn.plot.ly/plotly-latest.min.js"></script></head><body><div id="plotly-plot"></div><script>Plotly.react('plotly-plot', ${figureJSON});</script></body></html>`], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'plotly_figure.html';
  a.click();
  URL.revokeObjectURL(url);
}

const delta_dict={"hours":3600,"minutes":60,"days":3600*24,"seconds":1}

function download_request_to_debug() {
  const blob = new Blob([JSON.stringify(build_request_parameters())], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'gui_params.json';
  a.click();
  URL.revokeObjectURL(url);
}


function get_xaxis_I_above0(seuil){
  seuil = seuil || 1;
  DELTA_SECS = delta_dict['seconds']
  fig = document.getElementById('plotly_fig')
  current = fig.data.filter(x=>x.name=='CurrentPV')[0]
  condition = current.y.map(x=>x>seuil)
  let new_x=[0]

  for (let i = 1; i < current.x.length; i++) {
    val = new_x[new_x.length-1]
    if(condition[i]){
      val+=1
    }
    new_x.push(val);
  }
  return new_x
}

function transform_x_axis(){
  DELTA_SECS = delta_dict[DELTAT]
  fig = document.getElementById('plotly_fig')
  x = fig.data[0].x
  start = new Date(x[0]);

  // Calculate the time differences in seconds
  deltas = x.map((date) => (new Date(date) - start) / 1000);

  // Calculate differences between consecutive timestamps
  delta_diffs = [];
  for (let i = 1; i < deltas.length; i++) {
      delta_diffs.push(deltas[i] - deltas[i - 1]);
  }

  // Calculate the threshold (seuil) as the median of delta_diffs times 100
  seuil = median(delta_diffs) * 100;

  // Calculate the distance
  distance = median(delta_diffs) * DIS_FACTOR;

  // Calculate the new_x values
  new_x = [0];
  cumulativeDistance = 0;

  for (let i = 0; i < delta_diffs.length; i++) {
      if (delta_diffs[i] > seuil) {
          cumulativeDistance += distance;
      } else {
          cumulativeDistance += delta_diffs[i];
      }
      new_x.push(cumulativeDistance / DELTA_SECS);
  }

  // Median function
  function median(values) {
      values.sort((a, b) => a - b);
      middle = Math.floor(values.length / 2);
      if (values.length % 2 === 0) {
          return (values[middle - 1] + values[middle]) / 2;
      } else {
          return values[middle];
      }
  }
  return new_x
}

function formatDateTime(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    const milliseconds = String(date.getMilliseconds()).padStart(2, '0').slice(0,1)
    return `${year}-${month}-${day} ${hours}h${minutes}:${seconds}.${milliseconds}`;
}

function toggle_gaps(){
  fig = document.getElementById('plotly_fig')
  is_checked = document.getElementById('gap_switch').checked
  xx = [TIMES]
  title='timestamp(CET)'
  if (is_checked){
    method = document.getElementById('method_rgaps').value
    if (method=='I>1'){
      xx = [get_xaxis_I_above0()]
      title = 'datapoint number'
    }else {
      xx = [transform_x_axis()]
      title='elapsed time[' + DELTAT + ']'
    }
    // remove gaps and keep track of previous states
  }
  Plotly.restyle('plotly_fig', {x:xx})
  Plotly.relayout('plotly_fig', {xaxis:{title:title}})
  update_axes()
}


function update_traces_color(){
  config_colors = Array.from(TABLE_TAGS.children[0].children).slice(1,).map(x=>[x.children[1].textContent,x.children[2].children[0].value])
  for (let x of config_colors) {
    trace_id = fig.data.map(x=>x.name).indexOf(x[0])
    update = {
      'line.color':x[1],
      'marker.color':x[1],
    }
    Plotly.restyle('plotly_fig', update, trace_id);
  }
}

function addRow_tagTable(tagname,color) {
  loc_table_tags = get_active_table()
  list_tags = extract_listTags_from_html_table().map(x=>x[0])
  if (!list_tags.includes(tagname)) {
    var row = loc_table_tags.insertRow(loc_table_tags.rows.length);
    row.insertCell(0).innerHTML = '<input type="button" class="btn_delete" value = "X" onClick="deleteRow(this)">';
    // row.insertCell(1).innerHTML= '<b>'+tagname+'</b>';
    row.insertCell(1).innerHTML = tagname;
    if(!color){
      color = LIST_DISTINCT_COLORS[(Math.floor(Math.random() * LIST_DISTINCT_COLORS.length))];
    }
    row.insertCell(2).innerHTML =
    "<input id='color_" + tagname + "' class='color_button' type=button value="+ color + ' onClick=popup_trace_color_picker(this)>'
    btn = row.children[2].children[0]
    btn.style.backgroundColor = color
    btn.value = color
  }
}


function parse_tag(inputString){
  // Define a regular expression pattern to match the desired parts
  regexPattern = /(.*);(rgb\(\d+,\d+,\d+\))$/;
  matches = inputString.match(regexPattern);
  matches

  if (matches){
    return {tag:matches[1],color:matches[2]}
  }

  regexPattern = /(.*);(#\w{6})$/;
  matches = inputString.match(regexPattern);

  if (matches){
    return {tag:matches[1],color:matches[2]}
  }
  else {
    return {tag:inputString}
  }
}


function build_request_parameters() {
  let parameters = {}
  parameters['timerange'] = datetimepicker.value
  parameters['rs_time'] = document.getElementById('in_time_res').value + document.getElementById('dd_time_unit').value
  parameters['rs_method'] = document.getElementById('dd_resMethod').value
  parameters['tags'] = extract_listTags_from_html_table().map(x=>x[0])

  if (document.getElementById('btn_tab_dataset').classList.contains('active')){
    parameters['session'] = document.getElementById('dd_session').value
    parameters['data_set'] = document.getElementById('dd_data_set').value
    parameters['all_times'] = document.getElementById('check_times').checked
    parameters['all_tags'] = document.getElementById('check_all_tags').checked
    parameters['request_url'] =  '/generate_dataset_fig'
  }else if(document.getElementById('btn_tab_parameters').classList.contains('active')){
    parameters['model'] = document.getElementById('dd_models').value
    parameters['categorie'] = document.getElementById('dd_categorie').value
    parameters['coarse'] = document.getElementById('check_coarse').checked
    parameters['request_url'] =  '/generate_fig'
  }
  // console.log(parameters);
  return parameters
}

var TIMES
function fetch_figure() {
  btn_update.innerHTML = 'updating...'
  btn_update.classList.add('updating')
  let parameters = build_request_parameters()

  // remember visible states of previous traces
  if ($('#plotly_fig')[0].data==null){
    var tags_hidden=[]
  }else {
    var tags_hidden=$('#plotly_fig')[0].data.filter(x=>x.visible=='legendonly').map(x=>x.name)
  }
  // console.log(tags_hidden);

  $.post(parameters['request_url'],JSON.stringify(parameters),function(res,status){
    style = document.getElementById('dd_style').value

    var notif = res['notif']
    if ( notif!=200){
      alert(notif)
      $('#btn_update')[0].innerHTML='request data!'
      btn_update.classList.remove('updating')
    }
    var fig = JSON.parse(res['fig'])
    // make sure the colors are original state and the gaps as well
    $('#color_switch')[0].checked=false

    // plot the new figure
    Plotly.newPlot('plotly_fig', fig.data,fig.layout,CONFIG);
    for (trace of document.getElementById('plotly_fig').data){
      addRow_tagTable(trace.name)
    }
    TIMES = fig.data[0].x
    resize_figure()
    update_traces_color()
    update_hover()
    update_axes()
    update_size_markers()
    update_legend()
    modify_grid()
    update_table_traces()
    $('#btn_update')[0].innerHTML='request data!'
    btn_update.classList.remove('updating')
    let new_traces = plotly_fig.data.map(x=>x.name)
    for (trace of plotly_fig.data){
      trace.tag = trace.name
    }
    Plotly.restyle(plotly_fig,data)
    init_dropdown('select_dd_x',['Time'].concat(new_traces),change_x_axis)
    let indexes = tags_hidden.map(x=>new_traces.indexOf(x))
    if (indexes.length!=0){Plotly.restyle('plotly_fig', {visible:'legendonly'},indexes);}

    if (REAL_TIME) {
      if (REALTIME_CHECK.checked) {
        Plotly.relayout('plotly_fig', {'paper_bgcolor':PAPER_BG_COLOR_RT})
      }
    }
  })
}

function update_hover(){
  fig = document.getElementById('plotly_fig')
  text_date = TIMES.map(k=>formatDateTime(new Date(k)))
  precision = parseInt(document.getElementById('n_digits').value)
  units = Array()
  tag_x = document.getElementById('select_dd_x').value

  for (trace of fig.data){
    ynb = trace['yaxis'].slice(1,)
    len_data = trace.y.length
    yaxis_name = 'yaxis'+ynb
    unit = fig.layout[yaxis_name]['title']['text']
    units.push(Array(len_data).fill(unit))
  }
  update={
    customdata:units,
    customdata:units,
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
  Plotly.restyle('plotly_fig', update)
}



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


function addEnveloppe() {
  let fig = $('#plotly_fig')[0]
  parameters={fig_layout:fig.layout,fig_data:fig.data,tag:$('#dd_enveloppe')[0].value}
  $.post('/add_enveloppe',JSON.stringify(parameters),function(fig,status){
    // plot the new figure
    fig=JSON.parse(fig)
    FIG=fig
    Plotly.newPlot('plotly_fig', fig.data,fig.layout);
  })

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

function pop_menu(e){
  // console.log(e)
  let obj_html
  if (e.id.includes('version_title')){obj_html = $('#pop_version_info')[0]}
  else if (e.name=='button_eq'){obj_html = $('#pop_indicators')[0]}
  obj_html.style.display='block'
  obj_html.style.zIndex=10
}

function show_tag_list(e) {
  dd_div=document.getElementById(e.id.replace('in_',''))
  dd_div.style.display='block';
  dd_div.style.zIndex=10
}

function filterTag(e) {
  dd_div = document.getElementById(e.id.replace('in_',''))
  let filter = new RegExp(e.value.toUpperCase().replaceAll(' ','.*'));
  for (let a of dd_div.getElementsByTagName("a")) {
    let txtValue = a.textContent || a.innerText;
    if (filter.exec(txtValue.toUpperCase())!=null) {a.style.display = "";}
    else {a.style.display = "none";}
  }
}

// ----------------------------------
// FUNCTION TO INIT SOME COMPONENTS
function init_dropdown(dd_id,values,fun_on_click) {
  // console.log(dd_id);
  let dd_html=document.getElementById(dd_id)
  while (dd_html.options.length > 0) {
    dd_html.remove(0);
}
  // renove first elements
    for (const val of values)
    {
        var option = document.createElement("option");
        option.value = val;
        option.text = val.charAt(0).toUpperCase() + val.slice(1);
        if(fun_on_click){
          option.addEventListener("mouseup",()=>{fun_on_click()})
        }
        dd_html.appendChild(option);
    }
  }

function init_radioButton(rb_id,values,name){
  let rb_html=document.getElementById(rb_id)
  for (const val of values)
  {
      var div = document.createElement("div");
      var input = document.createElement("input");
      input.type = "radio";input.id=name+'_'+val;input.name=name;input.value=val;
      var label = document.createElement("label");
      label.setAttribute("for", name+'_'+val);
      label.append(document.createTextNode(val));
      div.appendChild(input)
      div.appendChild(label)
      rb_html.appendChild(div);
  }
}

function init_tags_dropdown(dd_id,values,fun_on_click) {
  let dd_html = document.getElementById(dd_id)
  while (dd_html.children.length > 0) {
    dd_html.removeChild(dd_html.children[0]);
  }
    for (const val of values)
    {
        var a = document.createElement("a");
        a.innerHTML = val;
        dd_html.appendChild(a);
        a.addEventListener("mouseup",()=>{fun_on_click(val)})
    }
}

// ----------------------------------------
// FUNCTIONS FOR LIST OF TAGS TABLE
function pop_listTags_up() {
  document.getElementById('popup_listTags').style.display='block'
  document.getElementById('popup_listTags').style.zIndex=10
  // retrieve the list of tags
  let listtags = extract_listTags_from_html_table().map(x=>x[0]+';'+x[1])
  document.getElementById('taglist').value=listtags.join('\n')
}

function empty_tableOfTags(){
  loc_table = get_active_table()
  nbrows = loc_table.rows.length
  for (let index=1;index<nbrows;index++){
    loc_table.deleteRow(1)
  }
}

function get_active_tab(){
  Array.from(document.getElementsByClassName("tab-button")).filter(x=>x.classList.contains('active'))[0].id
}

function get_active_table(){
  if (document.getElementById('btn_tab_dataset').classList.contains('active')){
    return table_tags_dataset
  }else if(document.getElementById('btn_tab_parameters').classList.contains('active')){
    return table_tags
  }
}

function apply_changes() {
  listtags = document.getElementById('taglist').value.split('\n').filter((el)=> {return el != ""}).map(x=>parse_tag(x))
  // delete all rows in TABLE_TAGS
  empty_tableOfTags(loc_table)
  // add rows
  for (tag of listtags) {
    color = tag['color']
    if (!color){
      color = LIST_DISTINCT_COLORS[(Math.floor(Math.random() * LIST_DISTINCT_COLORS.length))];
    }
    addRow_tagTable(tag['tag'],color)
  }
  // close the pop up
  document.getElementById('popup_listTags').style.display='none'
}

function extract_listTags_from_html_table() {
  loc_table = get_active_table()
  return Array.from(loc_table.children[0].children).slice(1,).map(x=>[x.children[1].innerHTML,x.children[2].children[0].value])
}

function select_tag_xaxis(tagname) {
  document.getElementById('select_dd_x').value = tagname
}

function deleteRow(obj) {
    var index = obj.parentNode.parentNode.rowIndex;
    loc_table = get_active_table()
    loc_table.deleteRow(index);
}

const LISTOPERATIONS = ['+','*','/','-','^']
function parse_formula(){
  formula = document.getElementById('in_formula').value
  // tags =
  // return
}

function computeArrayFromFormula(formula, data) {
  result = [];

  // Loop through each index of the arrays
  for (i = 0; i < data['var1'].length; i++) {
      // Create a temporary formula for evaluation
      tempFormula = formula;

      // Substitute the data with the actual values from the arrays
      for (variable in data) {
          regex = new RegExp(variable, 'g');
          tempFormula = tempFormula.replace(regex, data[variable][i]);
      }
      // Evaluate the formula and push the result to the result array
      result.push(eval(tempFormula));
  }
  return result;
}


function add_formula_variable(){

  data = document.getElementById('plotly_fig').data
  formula = document.getElementById('in_formula').value
  var variables = {}
  var var_names = {}
  for (opt of document.getElementById('dd_var').options){
      tmp = opt.value.split('_')
      varid = tmp[0]
      tag = tmp.slice(1,).join('_')
      variables[varid]= data.filter(x=>x.name==tag)[0].y
   }
  new_var = computeArrayFromFormula(formula, variables)
  new_var_name = document.getElementById('new_var_name').value
  // get the hightest number of y-axes
  highest_axisnb = Object.keys(fig.layout).filter(x=>x.includes('yaxis')).map(x=>parseInt(x.split('yaxis').slice(1,))).filter(x=>!isNaN(x))
  highest_axisnb = Math.max(...highest_axisnb)

  var layoutUpdate = {}
  layoutUpdate["yaxis" + String(highest_axisnb+1)] = {
     title: {text:new_var_name,font:{color:"black"}},
     overlaying: 'y',        // Overlay the new y-axis on top of the existing one
     side: 'right',
     position:0.5
  }
  // Use Plotly.relayout to update the layout of the existing figure
  Plotly.relayout('plotly_fig',layoutUpdate );
  // add the new trace
  new_trace = {
    x: data[0].x,
    y: new_var,
    name: new_var_name,
    type:"scattergl",
    line:{color:'black'},
    marker:{color:'black',size:5},
    yaxis:"y" + String(highest_axisnb+1)
  }
  Plotly.addTraces('plotly_fig', new_trace);
  update_axes()
  $('#dd_style')[0].dispatchEvent(new CustomEvent("change",{bubbles: true}));
  update_size_markers()
  addRow_tagTable(new_var_name)

}

function update_formula(){
  let formula = document.getElementById('in_formula').value
  for (opt of document.getElementById('dd_var').options){
     tmp = opt.value.split('_')
     varid = tmp[0]
     tag = tmp.slice(1,).join('_')
     regex = new RegExp(varid, 'g');
     formula = formula.replace(regex, tag);
   }
  document.getElementById('new_var_name').value = formula
}

function add_operation(e){
  operation = e.innerText
  formula = document.getElementById('in_formula')
  if (LISTOPERATIONS.includes(operation)){
    formula.value+=operation
  }
  else {
    tmp = document.getElementById('dd_var').value.split('_')
    varid = tmp[0]
    tag = tmp.slice(1,).join('_')
    formula.value += varid
  }
}

function update_dd_tag_for_formula() {
  dd_tags_formula=$('#dd_var')[0]
  // console.log(extract_listTags_from_html_table())
  previous_val = dd_tags_formula.value
  dd_tags_formula.innerHTML=''
  listtags = extract_listTags_from_html_table().map(x=>x[0])
  init_dropdown('dd_var', listtags)
}

function empyt_select(dd_id){
  cat_select = document.getElementById(dd_id)
  nb_children = cat_select.children.length
  for (k=0;k<nb_children;k++){
    cat_select.removeChild(cat_select.children[0])
  }
}

function change_model(){
  model = document.getElementById('dd_models').value
  $.post('/send_model_tags',JSON.stringify(model),function(data,status){
    model_tags = JSON.parse(data)
    empyt_select('dd_categorie')
    empyt_select('dd_y')
    init_tags_dropdown('dd_y',values=model_tags['all_tags'],addRow_tagTable)
    init_dropdown('dd_categorie',values=['no categorie'].concat(model_tags['categories']))
    // update timepicker
    max_date = moment(model_tags['max_date']).startOf('second').add(24*3600-1,'second')
    opt = {
      max_date:max_date,
      time_window:INITIAL_TIMEWINDOW,
      end_date:max_date,
      min_date:moment(model_tags['min_date']),
      excludeddates:model_tags['excludeddates']
    }
    update_timerange_picker(opt)
  }
)}

function get_sessions(){
  return new Promise((resolve, reject) => {
    $.get('send_sessions',function(sessions,status){
      // console.log(sessions)
      init_dropdown('dd_session',values=sessions)
      resolve()
    })
  })
}

function update_data_sets(){
  return new Promise(function(resolve, reject) {
    session = document.getElementById('dd_session').value
    $.post('send_data_sets',session,function(data_sets){
        document.getElementById("dd_data_set").innerHTML = ""
        init_dropdown('dd_data_set',values=data_sets)
        resolve()
    })
  });
}

function change_dataSet(){
  dataset = document.getElementById('dd_data_set').value
  session = document.getElementById('dd_session').value
  data={'dataset':dataset,'session':session}
  $.post('send_dfplc',JSON.stringify(data),function(tags,status){
    init_tags_dropdown('dd_y',values=tags,addRow_tagTable)
  })
}

//# ########################
//#    REAL TIME FEATURES  #
//# ########################
function update_timerange_picker(options){
  // let time_window = parseInt(document.getElementsByName('time_window')[0].value)
  time_window = options.time_window -1/60
  max_date = options.max_date || moment().startOf('second')
  end_date = options.end_date || max_date
  start_date = options.start_date || moment(end_date).subtract(time_window,'minute')
  min_date = options.min_date || moment('2022-01-01')
  excludeddates = options.excludeddates || []

  $('#datetimepicker').daterangepicker({
    timePicker: true,
    timePicker24Hour:true,
    timePickerSeconds:true,
    startDate:start_date,
    endDate:end_date,
    minDate:min_date,
    maxDate:max_date,
    showDropdowns:true,
    isInvalidDate: function(date) {
    var dateString = date.format('YYYY-MM-DD'); // Assuming you can format the date with the library
    return excludeddates.includes(dateString);
  },
    locale: {
      monthNamesShort: ['Janv.', 'Févr.', 'Mars', 'Avril', 'Mai', 'Juin', 'Juil.', 'Août', 'Sept.', 'Oct.', 'Nov.', 'Déc.'],
      monthNames: ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Aout","Septembre","Octobre","Novembre","Decembre"],
      format: 'D MMM YYYY HH:mm:ss',
      // format: 'D MMMM,YYYY HH:mm:ss'
    }
  })
}

function change_color_paper_background(color){
  Plotly.relayout('plotly_fig', {'paper_bgcolor':color});
}

function pop_menu_refresh(e) {
  // console.log(e.checked)
  if (e.checked) {
    document.getElementsByClassName('refresh_parameters')[0].style.opacity=1
    document.getElementsByClassName('parameters')[0].classList.add('realtime')
    Plotly.relayout('plotly_fig', {'paper_bgcolor':PAPER_BG_COLOR_RT});
  }
  else {
    document.getElementsByClassName('refresh_parameters')[0].style.opacity=0
    document.getElementsByClassName('parameters')[0].classList.remove('realtime')
    Plotly.relayout('plotly_fig', {'paper_bgcolor':'#fff'});
  }
}

// title of the graph callback
function change_title(e){
  // document.title='smallPower:'+e.value
  document.title=e.value
}

function pop_param_div(action){
  // console.log(action);
  let fig_container=document.getElementsByClassName('fig_container')[0]
  let param_div=document.getElementsByClassName('parameters')[0]
  // console.log(param_div.style.display);

  if (!STABLE_PARAMETERS_PANEL){
    if (action=='appear'){
      param_div.style.display='block'
    }else if (action=='disappear')
    {
      param_div.style.display='none'
    }
  }
  if (action=='toggle'){
    if (!STABLE_PARAMETERS_PANEL){
      param_div.style.display='block'
      STABLE_PARAMETERS_PANEL=true
      Plotly.relayout('plotly_fig', {'width': 1200});
    } else {
      param_div.style.display='none'
      STABLE_PARAMETERS_PANEL=false
      Plotly.relayout('plotly_fig', {'width': 1700});
    }
    // console.log('new STABLE_PARAMETERS_PANEL:'+STABLE_PARAMETERS_PANEL);
  }
}
//# ############################
//# HTML COLOR PICKER for plot #
//#      background            #
//# ############################
let width=400

function resize_figure(){
  Plotly.relayout('plotly_fig',{width:window.screen.width*0.75,height:window.screen.height*0.75})
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


function resize_domain(s){
  let xaxis = document.getElementById('plotly_fig').layout['xaxis']
  xaxis['domain']=[s,1-s]
  Plotly.relayout('plotly_fig',{xaxis:xaxis})
}

function popup_bg_color_picker(){
    picker = document.getElementById('bg_color_picker')
    picker.style.display = 'flex'
    picker.style.zIndex=1
  }
var cur_btn_color
function popup_trace_color_picker(e){
    picker = document.getElementById('trace_color_picker')
    cur_btn_color = e
    picker.style.display = 'flex'
    picker.style.zIndex=1
  }

function update_traces_color(){
  loc_table = get_active_table()
  config_colors = Array.from(loc_table.children[0].children).slice(1,).map(x=>[x.children[1].textContent,x.children[2].children[0].value])
  for (let x of config_colors) {
    // console.log(x);
    trace_id = document.getElementById('plotly_fig').data.map(x=>x.name).indexOf(x[0])
    update = {
      'line.color':x[1],
      'marker.color':x[1],
    }
    Plotly.restyle('plotly_fig', update, trace_id);
    }
}



function apply_traces_changes(){
  all_units = Array.from(table_traces.children[0].children).slice(1,).map(x=>x.children[2].children[0].value)
  all_units = Array.from(new Set(all_units));

  layout = {
  }

  layout['yaxis'] = {title: {text:all_units[0],font:{color:"black"}}}
  for (axis=2;axis<=all_units.length;axis++){
    layout['yaxis'+axis] = {
      title : {text:all_units[axis-1],font:{color:"black"}},
      overlaying: 'y',
    }
  }

  Plotly.relayout('plotly_fig', layout)


  for (row of Array.from(table_traces.children[0].children).slice(1,)){
    name = row.children[6].children[0].value
    color = row.children[1].textContent
    unit =  row.children[2].children[0].value
    row_id = row.children[3].children[0].value
    col = row.children[4].children[0].value
    size_mult = row.children[5].children[0].value

    id = fig.data.map(x=>x.name).indexOf(name)
    trace = fig.data[id]
    id_ax = all_units.indexOf(unit)+1
    if (id_ax==1){id_ax=""}
    axis = 'y' + id_ax
    console.log('axis of ' + name +' is' + axis);
    update = {
      yaxis:axis,
    }
    Plotly.restyle('plotly_fig', update, id)
  }

  //// delete unused axes
  layout = fig.layout
  axes = Object.keys(layout).filter(x=>x.includes("yaxis")).map(x=>x.slice(5,))
  for (k=all_units.length+1;k<=axes.length;k++){
    console.log('yaxis'+k);
    delete layout['yaxis'+k]
  }
  Plotly.relayout('plotly_fig', layout)
  update_axes()
}
