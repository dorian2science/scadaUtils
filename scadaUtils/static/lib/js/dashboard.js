// ########################
//#   GLOBAL VARIABLES    #
// ########################
REALTIME=false
var REALTIME_CHECK = document.getElementsByName('realtime_check')[0]
var datetimepicker = document.getElementById('datetimepicker')
var TABLE_TAGS = document.getElementById('table_tags')
var TIME_REFRESH_COUNTER = 0;
// var TIME_REFRESH_VALUE = parseInt(document.getElementsByName('in_refresh_time')[0].value)
const MIN_REFRESH_TIME = 0
const DEFAULT_TIME_REFRESH_VALUE = 50
const PAPER_BG_COLOR_RT = '#929dbf'
const LIST_DISTINCT_COLORS = ['#636EFA',
 '#EF553B',
 '#00CC96',
 '#AB63FA',
 '#FFA15A',
 '#19D3F3',
 '#FF6692',
 '#B6E880',
 '#FF97FF',
 '#FECB52',
 '#2E91E5',
 '#E15F99',
 '#1CA71C',
 '#FB0D0D',
 '#DA16FF',
 '#222A2A',
 '#B68100',
 '#750D86',
 '#EB663B',
 '#511CFB',
 '#00A08B',
 '#FB00D1',
 '#FC0080',
 '#B2828D',
 '#6C7C32',
 '#778AAE',
 '#862A16',
 '#A777F1',
 '#620042',
 '#1616A7',
 '#DA60CA',
 '#6C4516',
 '#0D2A63',
 '#AF0038',
 '#FD3216',
 '#00FE35',
 '#6A76FC',
 '#FED4C4',
 '#FE00CE',
 '#0DF9FF',
 '#F6F926',
 '#FF9616',
 '#479B55',
 '#EEA6FB',
 '#DC587D',
 '#D626FF',
 '#6E899C',
 '#00B5F7',
 '#B68E00',
 '#C9FBE5',
 '#FF0092',
 '#22FFA7',
 '#E3EE9E',
 '#86CE00',
 '#BC7196',
 '#7E7DCD',
 '#FC6955',
 '#E48F72',
 '#AA0DFE',
 '#3283FE',
 '#85660D',
 '#782AB6',
 '#565656',
 '#1C8356',
 '#16FF32',
 '#F7E1A0',
 '#E2E2E2',
 '#1CBE4F',
 '#C4451C',
 '#DEA0FD',
 '#FE00FA',
 '#325A9B',
 '#FEAF16',
 '#F8A19F',
 '#90AD1C',
 '#F6222E',
 '#1CFFCE',
 '#2ED9FF',
 '#B10DA1',
 '#C075A6',
 '#FC1CBF',
 '#B00068',
 '#FBE426',
 '#FA0087',
 'rgb(228,26,28)',
 'rgb(55,126,184)',
 'rgb(77,175,74)',
 'rgb(152,78,163)',
 'rgb(255,127,0)',
 'rgb(255,255,51)',
 'rgb(166,86,40)',
 'rgb(247,129,191)',
 'rgb(153,153,153)',
 'rgb(251,180,174)',
 'rgb(179,205,227)',
 'rgb(204,235,197)',
 'rgb(222,203,228)',
 'rgb(254,217,166)',
 'rgb(255,255,204)',
 'rgb(229,216,189)',
 'rgb(253,218,236)',
 'rgb(242,242,242)',
 'rgb(133, 92, 117)',
 'rgb(217, 175, 107)',
 'rgb(175, 100, 88)',
 'rgb(115, 111, 76)',
 'rgb(82, 106, 131)',
 'rgb(98, 83, 119)',
 'rgb(104, 133, 92)',
 'rgb(156, 156, 94)',
 'rgb(160, 97, 119)',
 'rgb(140, 120, 93)',
 'rgb(124, 124, 124)',
 '#636EFA',
 '#EF553B',
 '#00CC96',
 '#AB63FA',
 '#FFA15A',
 '#19D3F3',
 '#FF6692',
 '#B6E880',
 '#FF97FF',
 '#FECB52',
 '#2E91E5',
 '#E15F99',
 '#1CA71C',
 '#FB0D0D',
 '#DA16FF',
 '#222A2A',
 '#B68100',
 '#750D86',
 '#EB663B',
 '#511CFB',
 '#00A08B',
 '#FB00D1',
 '#FC0080',
 '#B2828D',
 '#6C7C32',
 '#778AAE',
 '#862A16',
 '#A777F1',
 '#620042',
 '#1616A7',
 '#DA60CA',
 '#6C4516',
 '#0D2A63',
 '#AF0038',
 '#FD3216',
 '#00FE35',
 '#6A76FC',
 '#FED4C4',
 '#FE00CE',
 '#0DF9FF',
 '#F6F926',
 '#FF9616',
 '#479B55',
 '#EEA6FB',
 '#DC587D',
 '#D626FF',
 '#6E899C',
 '#00B5F7',
 '#B68E00',
 '#C9FBE5',
 '#FF0092',
 '#22FFA7',
 '#E3EE9E',
 '#86CE00',
 '#BC7196',
 '#7E7DCD',
 '#FC6955',
 '#E48F72',
 '#AA0DFE',
 '#3283FE',
 '#85660D',
 '#782AB6',
 '#565656',
 '#1C8356',
 '#16FF32',
 '#F7E1A0',
 '#E2E2E2',
 '#1CBE4F',
 '#C4451C',
 '#DEA0FD',
 '#FE00FA',
 '#325A9B',
 '#FEAF16',
 '#F8A19F',
 '#90AD1C',
 '#F6222E',
 '#1CFFCE',
 '#2ED9FF',
 '#B10DA1',
 '#C075A6',
 '#FC1CBF',
 '#B00068',
 '#FBE426',
 '#FA0087',
 'rgb(228,26,28)',
 'rgb(55,126,184)',
 'rgb(77,175,74)',
 'rgb(152,78,163)',
 'rgb(255,127,0)',
 'rgb(255,255,51)',
 'rgb(166,86,40)',
 'rgb(247,129,191)',
 'rgb(153,153,153)',
 'rgb(251,180,174)',
 'rgb(179,205,227)',
 'rgb(204,235,197)',
 'rgb(222,203,228)',
 'rgb(254,217,166)',
 'rgb(255,255,204)',
 'rgb(229,216,189)',
 'rgb(253,218,236)',
 'rgb(242,242,242)',
 'rgb(133, 92, 117)',
 'rgb(217, 175, 107)',
 'rgb(175, 100, 88)',
 'rgb(115, 111, 76)',
 'rgb(82, 106, 131)',
 'rgb(98, 83, 119)',
 'rgb(104, 133, 92)',
 'rgb(156, 156, 94)',
 'rgb(160, 97, 119)',
 'rgb(140, 120, 93)',
 'rgb(124, 124, 124)']
var LIST_ORIGINAL_COLORS = []
var STABLE_PARAMETERS_PANEL=true
var TIMES = []
var FIG
DIS_FACTOR=0
DELTAT='seconds'
var CONFIG = {
  showEditInChartStudio: false,
  locale: 'fr',
  displaylogo: false,
  plotlyServerURL: "https://chart-studio.plotly.com",
  editable:false,
  modeBarButtonsToRemove: ['select2d','lasso2d'],
  modeBarButtonsToAdd: ['toggleSpikelines','lasso2d','toggleHover'],
}

// ########################
// #      FUNCTIONS       #
// ########################
function update_legend() {
  let mode=Array.from($('input[type=radio][name=legend]')).filter(x=>x.checked)[0].value
  // console.log(mode)
  if (mode=='unvisible') {
    Plotly.restyle('plotly_fig', {'showlegend': false});
  } else {
    Plotly.restyle('plotly_fig', {'showlegend': true})
    let tags=Array.from($('.legendtext')).map(x=>x.dataset.unformatted)
    $.post('/send_description_names',JSON.stringify({mode:mode,tags:tags}),function(data,status){
      // console.log(data);
      let new_names=JSON.parse(data)
      new_names=Object.values(new_names)
      // console.log(new_names);
      update={
        'name':new_names,
        'showlegend': true
      }
      Plotly.restyle('plotly_fig', update);
    })
  }
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

function export_figure() {
    // Convert the figure to HTML
    let fig = document.getElementById('plotly_fig')
    $.post('/exportFigure',JSON.stringify({data:fig.data,layout:fig.layout}),function(res,status){
      var status=res['status']
      if( status=='ok') {
      // Create an anchor element for downloading
      url = res['filename']
      a = document.getElementById('download-link')
      a.href = url;
      a.download = 'plotly_figure.html';

      // Trigger a click event on the anchor element to start the download
      a.click();

      // Clean up by revoking the URL
      URL.revokeObjectURL(url);
      }else {
        alert(res['notif'])
      }
    })

  };

const delta_dict={"hours":3600,"minutes":60,"days":3600*24,"seconds":1}
function transform_x_axis(){
  DELTA_SECS=delta_dict[DELTAT]
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

    return `${year}-${month}-${day} ${hours}h${minutes}:${seconds}`;
}

function toogle_gaps(){
  fig = document.getElementById('plotly_fig')
  is_checked = document.getElementById('gap_switch').checked
  if (is_checked){
    x_wo_gaps = transform_x_axis()
    // remove gaps and keep track of previous states
    update = {
      x:[x_wo_gaps],
    }
    Plotly.relayout('plotly_fig', {xaxis:{title:'elapsed time[' + DELTAT + ']'}});
  }else{
    // get back to timestamps
    update={
      x:[TIMES],
    }
    Plotly.relayout('plotly_fig', {xaxis:{title:'time(CET)'}});
}
Plotly.restyle('plotly_fig', update)
}

function build_request_parameters() {
  let parameters={}
  parameters['timerange']=datetimepicker.value
  parameters['rs_time']=document.getElementById('in_time_res').value
  parameters['rs_method']=document.getElementById('dd_resMethod').value
  parameters['categorie']=document.getElementById('dd_categorie').value
  parameters['x']=document.getElementById('select_dd_x').value
  parameters['tags']=extract_listTags_from_html_table()
  return parameters
}

function fetch_figure() {
  let btn_update=$('#btn_update')[0]
  btn_update.innerHTML='updating...'
  btn_update.classList.add('updating')
  let parameters = build_request_parameters()
  // remember visible states of previous traces
  if ($('#plotly_fig')[0].data==null){
    var tags_hidden=[]
  }else {
    var tags_hidden=$('#plotly_fig')[0].data.filter(x=>x.visible=='legendonly').map(x=>x.name)
  }
  // console.log(tags_hidden);
  // post request
  $.post('/generate_fig',JSON.stringify(parameters),function(res,status){
    style = document.getElementById('dd_style').value

    var notif = res['notif']
    var fig = JSON.parse(res['fig'])
    // make sure the colors are original state and the gaps as well
    $('#color_switch')[0].checked=false

    // plot the new figure
    Plotly.newPlot('plotly_fig', fig.data,fig.layout,CONFIG);
    resize_figure()
    update_hover()
    update_axes()
    update_size_markers()
    update_button_colors()
    update_legend()
    modify_grid()
    // update finish
    $('#btn_update')[0].innerHTML='request data!'
    btn_update.classList.remove('updating')
    if ( notif!=200){
      alert(notif)
      return
    }
    let new_traces = $('#plotly_fig')[0].data.map(x=>x.name)
    let indexes = tags_hidden.map(x=>new_traces.indexOf(x))
    if (indexes.length!=0){Plotly.restyle('plotly_fig', {visible:'legendonly'},indexes);}
    if (REALTIME) {
      if (REALTIME_CHECK.checked) {
        Plotly.relayout('plotly_fig', {'paper_bgcolor':PAPER_BG_COLOR_RT})
      }
    }
  })
}

function update_hover(){

  fig = document.getElementById('plotly_fig')
  TIMES = fig.data[0].x
  text_date = TIMES.map(k=>formatDateTime(new Date(k)))
  precision = parseInt(document.getElementById('n_digits').value)

  units = Array()
  for (trace of fig.data){
    ynb = trace['yaxis'].slice(1,)
    len_data = trace.y.length
    yaxis_name = 'yaxis'+ynb
    unit = fig.layout[yaxis_name]['title']['text']
    units.push(Array(len_data).fill(unit))
  }
  update={
    customdata:units,
    text:[text_date],
    hovertemplate : '<i>value</i>: %{y:.'+precision+'f} %{customdata}<br>'+'<b>%{text}</b>',
    hoverlabel:{
        // bgcolor:"white",
        font:{size:parseInt(document.getElementById('fs_hover').value)},
        font_family:"Rockwell"
  }
}
  Plotly.restyle('plotly_fig', update)

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
function modify_grid(){
  layout = document.getElementById('plotly_fig').layout
  xaxis=layout['xaxis']

  let grid_box = {
    linecolor: '#636363',
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

function update_axes(){


  layout = document.getElementById('plotly_fig').layout
  axes = Object.keys(layout).filter(x=>x.includes('yaxis')).reduce((obj, key) => {
    obj[key] = layout[key];
    return obj;
  }, {})
  new_layout = {}
  var k = 0
  var p1 = 0
  var p2 = 1
  // s = parseFloat(document.getElementById('s_axes').value)
  s =0.06
  // console.log("space",s);
  for (axisname in axes){
    curaxis = axes[axisname]
    if (k%2){
      p = p1
      p1+=s
      curaxis['side'] = 'left'
    }else{
      p = p2
      p2-=s
      curaxis['side'] = 'right'
    }
    k++
    ax_col = curaxis['title']['font']['color']
    curaxis['linecolor'] = ax_col
    curaxis['linewidth'] = 4
    curaxis['autotick']= true
    // curaxis['nticks'] = parseFloat(document.getElementById('nticks').value)
    curaxis['nticks'] = 10
    curaxis['ticks'] = 'outside'
    curaxis['tick0'] = 0
    curaxis['dtick'] = 0.15
    curaxis['ticklen'] = 8
    curaxis['title'] = {
        text: curaxis['title']['text'],
        font: curaxis['title']['font'],
        standoff: 0, // Adjust the standoff to move the title outside
      },
    curaxis['tickwidth'] = 2
    curaxis['tickcolor'] = ax_col
    curaxis['position'] = p
    new_layout[axisname] = curaxis

  }
  xaxis=layout['xaxis']
  minis = -1.0*s
  xaxis['domain']=[p1+minis,p2-minis]
  new_layout['xaxis'] = xaxis
Plotly.relayout('plotly_fig', new_layout)

}
var converter = new showdown.Converter()
// $('#pop_indicators').load('../static/html/indicators.html')

function pop_menu(e){
  // console.log(e)
  let obj_html
  if (e.id.includes('version_title')){obj_html = $('#pop_version_info')[0]}
  else if (e.name=='button_eq'){obj_html = $('#pop_indicators')[0]}
  obj_html.style.display='block'
  obj_html.style.zIndex=10
}

// ----------------------------------
// TAGS DROPDOWN
function show_tag_list(e) {
  dd_div=document.getElementById(e.id.replace('in_',''))
  dd_div.style.display='block';
  dd_div.style.zIndex=10
}

function filterTag(e) {
  // console.log(e.id);
  dd_div=document.getElementById(e.id.replace('in_',''))
  let filter = new RegExp(e.value.toUpperCase().replaceAll(' ','.*'));
  // console.log(filter);
  for (let a of dd_div.getElementsByTagName("a")) {
    let txtValue = a.textContent || a.innerText;
    if (filter.exec(txtValue.toUpperCase())!=null) {a.style.display = "";}
    else {a.style.display = "none";}
  }
}

// ----------------------------------
// FUNCTION TO INIT SOME COMPONENTS
function init_dropdown(dd_id,values) {
  let dd_html=document.getElementById(dd_id)
    for (const val of values)
    {
        var option = document.createElement("option");
        option.value = val;
        option.text = val.charAt(0).toUpperCase() + val.slice(1);
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
  let dd_html=document.getElementById(dd_id)
    for (const val of values)
    {
        var a = document.createElement("a");
        // option.value = val;
        a.innerHTML = val;
        // a.href = '#'+a.innerHTML;
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
  let listtags = extract_listTags_from_html_table()
  document.getElementById('taglist').value=listtags.join('\n')
}

function apply_changes() {
  let listtags=document.getElementById('taglist').value.split('\n')
  listtags = listtags.filter((el)=> {return el != ""});

  // delete all rows in TABLE_TAGS
  let nbrows=TABLE_TAGS.rows.length
  for (let index=1;index<nbrows;index++){TABLE_TAGS.deleteRow(1);}
  // add rows
  for (tag of listtags) {addRow_tagTable(tag)}
  // close the pop up
  document.getElementById('popup_listTags').style.display='none'

}

function extract_listTags_from_html_table() {
  let listTags=[]
  let listrows= TABLE_TAGS.children[0].children
  for (let row of listrows) {
    // console.log(row.children[1].innerHTML);
    listTags.push(row.children[1].innerHTML)
  }
  return listTags.slice(1,)
}

function addRow_tagTable(tagname) {
    if (!extract_listTags_from_html_table().includes(tagname)) {
      var row = TABLE_TAGS.insertRow(TABLE_TAGS.rows.length);
      row.insertCell(0).innerHTML= '<input style="width:35px" type="button" value = "X" onClick="deleteRow(this)">';
      // row.insertCell(1).innerHTML= '<b>'+tagname+'</b>';
      row.insertCell(1).innerHTML= tagname;
      row.insertCell(2).innerHTML= '<input id=color_' + tagname + ' class="color_button" type="button" value=color onClick="popup_trace_color_picker(this)">';;
  }
  update_dd_enveloppe()
}

function select_tag_xaxis(tagname) {
  document.getElementById('select_dd_x').value = tagname
}

function deleteRow(obj) {
    var index = obj.parentNode.parentNode.rowIndex;
    TABLE_TAGS.deleteRow(index);
    update_dd_enveloppe()
}

function update_dd_enveloppe() {
  let dd_enveloppe=$('#dd_enveloppe')[0]
  // console.log(extract_listTags_from_html_table())
  let previous_val=dd_enveloppe.value
  dd_enveloppe.innerHTML=''
  let listtags=['no tag'].concat(extract_listTags_from_html_table())
  init_dropdown('dd_enveloppe', listtags)
  if (listtags.includes(previous_val)) {
    dd_enveloppe.value=previous_val
  } else{
    dd_enveloppe.value='no tag'
  }
}

//# ###########################
//# Backend INITIALIZATION    #
//# ###########################
$.when(
  $.get('init',function(data) {
    data=JSON.parse(data)
    // ------- INITIALIZATION of myDropdown menus --------
    init_dropdown('dd_resMethod',values=data['rsMethods'])
    init_dropdown('dd_style',values=data['styles'])
    init_dropdown('dd_categorie',values=['no categorie'].concat(data['categories']))
    init_dropdown('dd_operation',values=['no operation'].concat(['derivative','integral','regression p1','regression p2','regression p3']))
    init_tags_dropdown('dd_y',values=data['all_tags'],addRow_tagTable)
    init_tags_dropdown('dd_x',values=['time'].concat(data['all_tags']),select_tag_xaxis)
    init_dropdown('select_dd_x',values=['time'].concat(data['all_tags']))
    init_radioButton(id='legend_para',values=['unvisible','tag','description'],'legend')
    $('input[type=radio][name=legend]').change(function() {
      update_legend(this.value)
    })

    //--------- DEFAULT VALUES FOR REQUEST_PARAMETERS ------------
    // console.log(data);
    data['tags'].map(tag=>addRow_tagTable(tag) )
    $('#dd_resMethod')[0].value="mean"
    $('#gap_switch')[0].checked=false
    $('#legend_tag')[0].checked=true;
    $('#dd_enveloppe')[0].value="no tag"
    $('#dd_operation')[0].value="no operation"
    $('#select_dd_x')[0].value="time"
    // $('#select_dd_x')[0].value=data['x']
    $('#in_time_res')[0].value=data['rs']
    $('.title_fig')[0].value=data['fig_name']

    DELAY_REAL_TIME = data['delay_minutes']
    $(update_timerange_picker(DELAY_REAL_TIME))
    if (REALTIME){
      document.getElementsByName('time_window')[0].value=data['time_window']
      // DEFAULT REAL-TIME
      let refresh_time=document.getElementsByName('in_refresh_time')[0]
      refresh_time.value=DEFAULT_TIME_REFRESH_VALUE
      refresh_time.min=MIN_REFRESH_TIME
      REALTIME_CHECK.checked=false;
  }


    document.title=data['title'] +':'+$('.title_fig')[0].value
    // path_log_version='../static/lib/'+data['log_versions']
    path_log_version='../static/lib/log_versions.md'
    // ****** load the logversion file info ******
    $.get(path_log_version, function(md_text) {
      $('#pop_version_info')[0].innerHTML=converter.makeHtml(md_text)
    })
    //BUILD THE INITIAL FIGURE
    fetch_figure()
    // data2excel()
  }),
)

//# ########################
//#    REAL TIME FEATURES  #
//# ########################
function update_timerange_picker(delay=0) {
  let time_window = parseInt(document.getElementsByName('time_window')[0].value)
  let start = moment().startOf('second').subtract(delay,'minute').subtract(time_window,'minute')
  let end = moment().startOf('second').subtract(delay,'minute')
  $('input[name="datetimes"]').daterangepicker({
    timePicker: true,
    timePicker24Hour:true,
    timePickerSeconds:true,
    // startDate:start,
    // endDate:end,
    startDate:"7 September,2023 08:43:42",
    endDate:end,

    maxDate:end,
    locale: {
      monthNamesShort: ['Janv.', 'Févr.', 'Mars', 'Avril', 'Mai', 'Juin', 'Juil.', 'Août', 'Sept.', 'Oct.', 'Nov.', 'Déc.'],
      // format: 'd-MMM-YY HH:mm',
      monthNames: ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Aout","Septembre","Octobre","Novembre","Decembre"],

      format: 'D MMMM,YYYY HH:mm:ss'
    }
  });
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
if (REALTIME){
// update TIME_REFRESH_VALUE on pressing enter
  document.getElementsByName('in_refresh_time')[0].onkeyup=function(e){
    if (e.key=='Enter'){
      let value = parseInt(document.getElementsByName('in_refresh_time')[0].value)
      if (value<MIN_REFRESH_TIME){
        alert('please select a refresh time value > '+ (MIN_REFRESH_TIME-1) +' seconds')
      }else
      {
        TIME_REFRESH_VALUE=value
        TIME_REFRESH_COUNTER=TIME_REFRESH_VALUE
      }
    }
  }
  // update datetimepicker if in refresh mode
  setInterval(()=>{
    if (REALTIME_CHECK.checked){
      if (TIME_REFRESH_COUNTER==0) {
        TIME_REFRESH_COUNTER = TIME_REFRESH_VALUE
        update_timerange_picker()
        fetch_figure()
      }
      // console.log(TIME_REFRESH_COUNTER)
      TIME_REFRESH_COUNTER-=1
    }
  },1000)
}
// title of the graph callback
function change_title(e){
  // document.title='smallPower:'+e.value
  document.title=e.value
}
//# #########################
//#  LISTENERS to hide menus#
//#   when clicking outside #
//#       of them           #
//# #########################
//
var listpop_ids=['popup_listTags',"dd_x","dd_y","pop_version_info","pop_indicators","bg_color_picker","trace_color_picker"]
// var listpop_ids=['popup_listTags',"dd_x","dd_y","pop_version_info","pop_indicators"]
document.addEventListener("mouseup", function(event) {
  for (id of listpop_ids) {
    var html_obj = document.getElementById(id);
    if (!html_obj.contains(event.target)) {
        html_obj.style.display='none'
        html_obj.style.zIndex=-1
    }
  }
});

//# ##################
//#       SHORTCUTS  #
//# ##################
document.getElementById('plotly_fig').onkeyup=function(e){
// document.onkeyup=function(e){
  // console.log('shortcut triggered');
  if (e.key == 't') {$('#legend_tag')[0].checked=true;update_legend($('input[name="legend"]')[0].value)}
  else if (e.key == 'd') {$('#legend_description')[0].checked=true;update_legend($('input[name="legend"]')[0].value)}
  else if (e.key == 'u') {$('#legend_unvisible')[0].checked=true;update_legend($('input[name="legend"]')[0].value)}
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
var CURTRACE = 0

AColorPicker.from('#bg_color_picker',{'hueBarSize':[width-60,50],'slBarSize':[width,150]})
.on('change', (picker, color) => {
  hex_color_value=AColorPicker.parseColor(color, "hex");
  console.log('bg');
  Plotly.relayout('plotly_fig', {'plot_bgcolor':color})
})

AColorPicker.from('#trace_color_picker',{'hueBarSize':[width-60,50],'slBarSize':[width,150]})
.on('change', (picker, color) => {
  hex_color_value=AColorPicker.parseColor(color, "hex");
  console.log(hex_color_value,CURTRACE);
  update = {
    'line.color':hex_color_value,
    'marker.color':hex_color_value,
  }
  Plotly.restyle('plotly_fig', update, CURTRACE);
  update_button_colors()
});

function update_button_colors(){
  for (trace of fig.data){
    id = 'color_' + trace.name
    color = trace.marker.color
    // console.log(id,color);
    btn = document.getElementById(id)
    btn.style.backgroundColor=color
    btn.value = color
  }
}

function test(){

layout = document.getElementById('plotly_fig').layout
curaxis = 'yaxis3'
axis = layout[curaxis]
// axis['range']=[0,1000]
axis['tickvals'] = ['0','2','6','8','10']
axis['ticktext'] = ['0','2','6','8','10']
axis['range'] = [0,60]
axis['autorange'] = false
axis['showgrid'] = true
layout[curaxis] = axis
Plotly.relayout('plotly_fig', layout)
layout = document.getElementById('plotly_fig').layout
axis = layout[curaxis]
axis

layout = document.getElementById('plotly_fig').layout
curaxis = 'yaxis'
axis = layout[curaxis]
axis['range'] = [0,700]
axis['showgrid'] = true
layout[curaxis] = axis
Plotly.relayout('plotly_fig', layout)
layout = document.getElementById('plotly_fig').layout
axis = layout[curaxis]
axis

}

function resize_figure(){
  Plotly.relayout('plotly_fig',{width:window.screen.width*0.75,height:window.screen.height*0.75})
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
function popup_trace_color_picker(e){
    picker = document.getElementById('trace_color_picker')
    CURTRACE = fig.data.map(x=>x.name).indexOf(e.id.split('color_')[1])
    picker.style.display = 'flex'
    picker.style.zIndex=1
  }
