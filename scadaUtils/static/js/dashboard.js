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

function addRow_tagTable(tagname) {
  loc_table_tags = get_active_table()
  list_tags = extract_listTags_from_html_table()
  if (!list_tags.includes(tagname)) {
    var row = loc_table_tags.insertRow(loc_table_tags.rows.length);
    row.insertCell(0).innerHTML = '<input type="button" class="btn_delete" value = "X" onClick="deleteRow(this)">';
    // row.insertCell(1).innerHTML= '<b>'+tagname+'</b>';
    row.insertCell(1).innerHTML = tagname;
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
  parameters['tags'] = extract_listTags_from_html_table()
  parameters['tab'] = get_active_tab()

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
    parameters['high_res'] = document.getElementById('check_hr').checked
    parameters['request_url'] =  '/generate_fig'
  }
  // console.log(parameters);
  return parameters
}

var DATA, LAST_REQUEST
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
  LAST_REQUEST = JSON.stringify(parameters)
  // console.log("sending request");
  $.post(parameters['request_url'],LAST_REQUEST,function(res,status){
    // threat the notification message sent by the backend
    var notif = res['notif']
    console.log(notif);
    DATA = res
    if ( notif!=200){
      alert(notif)
      $('#btn_update')[0].innerHTML='request data!'
      btn_update.classList.remove('updating')
    }
    console.log('data received');
    // turn off the new_colors and the gaps switches
    $('#color_switch')[0].checked=false
    // plot the new figure
    data2plot = []
    tags = Object.keys(res['data'])
    all_units = Array.from(new Set(Object.values(res['units']))).map((v, k) => ({ [v]: k +1})).reduce((acc, obj) => ({ ...acc, ...obj }), {});

    
    x = DATA['Time']
    if (check_hr.checked){
      btn_hr_t0.max = x.length
      time_window = parseInt(in_window_hr.value)
      t0 = parseInt(btn_hr_t0.value)
      t1 = t0 + time_window
      x = x.slice(t0,t1)
    }
    for (k=0;k<tags.length;k++){
      tag = tags[k]
      y = DATA['data'][tag]
      if (check_hr.checked){
        y = y.slice(t0,t1)
      }
      // console.log(tag)
      unit = res['units'][tag]
      new_trace = {
        x : x,
        y : y,
        yaxis : 'y11'+all_units[unit],
        xaxis : 'x',
        marker : {"color":LIST_DISTINCT_COLORS[k]},
        tag : tag,
        name : tag,
        type : 'scattergl',
        unit : unit,
      }
      data2plot.push(new_trace) 
    }
    console.log('done');
    layout = {'xaxis':{'type':'date','domain':[0.05,0.95]},'yaxis111':create_std_axis()}
    
      
    Plotly.newPlot('plotly_fig', data2plot,layout,CONFIG).then(()=>{
      // update the table of traces to load the planche
      update_table_traces()
      .then(()=>{
        // reposition the traces according to their layout
        for (k=1;k<table_traces.rows.length-1;k++){
          e = table_traces.rows[k].children[3].children[0]
          console.log(e.value);
          // e.dispatchEvent(new Event("change"));
        }
        redefine_x_domains()
        overlay_y_axes()
        auto_resize_figure()
        update_size_markers()
        update_traces_color()
        update_style_fig()
        update_hover()
        build_layout_from_planch()
        update_dd_tag_for_formula()
        empty_table(table_computed_vars)
        // update_legend()
        // modify_grid()
        $('#btn_update')[0].innerHTML='request data!'
        btn_update.classList.remove('updating')

        // let indexes = tags_hidden.map(x=>new_traces.indexOf(x))
        // if (indexes.length!=0){Plotly.restyle('plotly_fig', {visible:'legendonly'},indexes);}
  
      })
      // update the dropdown menu to change the x-axis
      init_dropdown('select_dd_x',['Time'].concat(tags),change_x_axis)
    });
  })
}

function overlay_y_axes(){
  // overlaying the y-axes
  yl = Array.from(Object.keys(plotly_fig.layout)).filter(y=>y.includes('yaxis') && y!='yaxis111')
  yl2 = {}
  for (k=0;k<yl.length;k++){
    sp = yl[k].slice(5,7)
    yl2[yl[k]+'.overlaying']='y'+sp+'1'
    transform_2_std_axis(yl[k])
  }
  Plotly.relayout("plotly_fig",yl2)
  .then(()=>{
    reposition_yaxes()
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


// FUNCTIONS FOR LIST OF TAGS TABLE
function pop_listTags_up() {
  document.getElementById('popup_listTags').style.display='block'
  document.getElementById('popup_listTags').style.zIndex=10
  // retrieve the list of tags
  let listtags = extract_listTags_from_html_table()
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
  return Array.from(document.getElementsByClassName("tab-button")).filter(x=>x.classList.contains('active'))[0].id.split('_').slice(1,).join('_')
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
    addRow_tagTable(tag['tag'])
  }
  // close the pop up
  document.getElementById('popup_listTags').style.display='none'
}

function update_high_res_data(){
  time_window = parseInt(in_window_hr.value)
  t0 = parseInt(btn_hr_t0.value)
  t1 = t0 + time_window
  x = [DATA['Time'].slice(t0,t1)]

  for (tag in DATA['data']){
    y = [DATA['data'][tag].slice(t0,t1)]
    Plotly.restyle("plotly_fig",{'x':x,'y':y},plotly_fig.data.map(x=>x.tag).indexOf(tag)).then(()=>{
      update_ticks()
    })
  }
}

function increment_high_res(inc){
  btn_hr_t0.value = parseInt(btn_hr_t0.value) + inc
  update_high_res_data()
}

function extract_listTags_from_html_table() {
  loc_table = get_active_table()
  return Array.from(loc_table.children[0].children).slice(1,).map(x=>x.children[1].textContent)
}

function select_tag_xaxis(tagname) {
  document.getElementById('select_dd_x').value = tagname
}

function deleteRow(obj) {
    var index = obj.parentNode.parentNode.rowIndex;
    loc_table = get_active_table()
    loc_table.deleteRow(index);
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
    // console.log('changing tags from model');
    init_dropdown('dd_categorie',values=['no categorie'].concat(model_tags['categories']))
    init_tags_dropdown('dd_y',values=model_tags['all_tags'],addRow_tagTable)
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

function toggle_check(check_id,div_id){
  div = document.getElementById(div_id)
  check = document.getElementById(check_id)
  if (check.checked){
    div.style.display='inline-block'
  }else{
    div.style.display='none'
  }

}

function toggle_real_time(){
  if (check_rt.checked){
    in_rt_time_window.style.display='inline-block'
    in_rt_time_window.previousElementSibling.style.display='inline-block' 
    in_rt_refresh.style.display='inline-block'
    in_rt_refresh.previousElementSibling.style.display='inline-block'
  }else{
    in_rt_time_window.style.display='none'
    in_rt_time_window.previousElementSibling.style.display='none' 
    in_rt_refresh.style.display='none'
    in_rt_refresh.previousElementSibling.style.display='none'

  }
}

function get_sessions(){
  return new Promise((resolve, reject) => {
    $.get('send_sessions',function(sessions,status){
      init_dropdown('dd_session',values=sessions.sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase())))
      .then(()=>{
        dd_session.value = INIT_DATA['initial_session']
        resolve()
      })
    })
  })
}

function update_data_sets(){
  // console.log("get datasets");
  return new Promise(function(resolve, reject) {
    session = document.getElementById('dd_session').value
    $.post('send_data_sets',session,function(data_sets){
        document.getElementById("dd_data_set").innerHTML = ""
        init_dropdown('dd_data_set',values=data_sets.sort((a, b) => b.localeCompare(a)))
        .then(()=>{
          // console.log(data_sets);
          resolve()
        })
    })
  });
}

function update_filter_tags(){
  session = document.getElementById('dd_session').value
  dataset = document.getElementById('dd_data_set').value
  data = {'dataset':dataset,'session':session}
  $.post('send_dfplc',JSON.stringify(data),function(tags,status){
    init_tags_dropdown('dd_y',values=tags,addRow_tagTable)
  })
}

function change_dataSet(){
  // console.log(data)
  empty_tableOfTags()
  update_filter_tags()
  // console.log('changing tags from dataset');
}

//# ########################
//#    REAL TIME FEATURES  #
//# ########################
function real_time(){
  if (check_rt.checked && COUNTER<0){
    t1 = moment().format('DD MMM YYYY HH:mm:ss')
    t0 = moment().subtract(in_rt_time_window.value,'minute').format('DD MMM YYYY HH:mm:ss')
    dt =t0 + ' - '+ t1
    datetimepicker.value = dt
    '16 Jan 2024 12:00:00 - 17 Jan 2024 23:59:59' 
    btn_update.click()
    COUNTER = in_rt_refresh.value
  }
  COUNTER -=0.5 
}

var COUNTER=0
setInterval(real_time,500)

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

function auto_resize_figure(){
  Plotly.relayout('plotly_fig',{width:window.screen.width*0.55,height:window.screen.height*0.55})
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

