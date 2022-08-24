// ########################
//#   GLOBAL VARIABLES    #
// ########################
var REALTIME_CHECK=document.getElementsByName('realtime_check')[0]
var datetimepicker=document.getElementById('datetimepicker')
var TABLE_TAGS=document.getElementById('table_tags')
var TIME_REFRESH_COUNTER = 0;
var TIME_REFRESH_VALUE=parseInt(document.getElementsByName('in_refresh_time')[0].value)
const MIN_REFRESH_TIME=2
const DEFAULT_TIME_REFRESH_VALUE=50
const PAPER_BG_COLOR_RT='#929dbf'

// ########################
//#       FUNCTIONS       #
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
      let new_names=JSON.parse(data)
      new_names=Object.values(new_names)
      // console.log(new_names);
      update={
        'name':new_names,
        // 'name':['cooli','second'],
        'showlegend': true
      }
      Plotly.restyle('plotly_fig', update);
    })
  }
}

function data2excel(){
  let fig=document.getElementById('plotly_fig')
  $.post('/export2excel',JSON.stringify({data:fig.data,layout:fig.layout}),function(path_to_file,status){
    if( typeof(path_to_file)=='string') {
      console.log(path_to_file)
      window.open(path_to_file)
    }else {
      alert('impossible to generate your excel file, please report the bug.')
    }
  })
}

function build_request_parameters() {
  let parameters={}
  parameters['timerange']=datetimepicker.value
  parameters['rs_time']=document.getElementById('in_time_res').value
  parameters['rs_method']=document.getElementById('dd_resMethod').value
  parameters['categorie']=document.getElementById('dd_categorie').value
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
  $.post('/generate_fig',JSON.stringify(parameters),function(fig,status){
    style =document.getElementById('dd_style').value
    var fig=JSON.parse(fig)
    // plot the new figure
    Plotly.newPlot('plotly_fig', fig.data,fig.layout);
    // update the legend
    update_legend()
    // hide the old legendonly traces
    let new_traces=$('#plotly_fig')[0].data.map(x=>x.name)
    let indexes=tags_hidden.map(x=>new_traces.indexOf(x))
    // console.log(indexes);
    if (indexes.length!=0){Plotly.restyle('plotly_fig', {visible:'legendonly'},indexes);}
    if (REALTIME_CHECK.checked) {
      Plotly.relayout('plotly_fig', {'paper_bgcolor':PAPER_BG_COLOR_RT})
    }
    // update finish
    $('#btn_update')[0].innerHTML='get my data!'
    btn_update.classList.remove('updating')

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
    // marker_line_width:0.2,
    // marker_size:6,
    // line_width:3
  }
  Plotly.restyle('plotly_fig', update);
}

function pop_menu(e){
  console.log(e)
  let obj_html
  if (e.id.includes('version_title')){obj_html = $('#pop_version_info')[0]}
  else if (e.name=='button_eq'){obj_html = $('#pop_equations')[0]}
  obj_html.style.display='block'
  obj_html.style.zIndex=10
}

// ----------------------------------
// TAGS DROPDOWN
function show_tag_list(e) {
  e.value=''
  ddtags = document.getElementById("dd_tags")
  ddtags.style.display='block';
  dd_tags.style.zIndex=10
}

function filterTag() {
  let input = $(".in_dd_tag")[0];
  let filter = new RegExp(input.value.toUpperCase().replaceAll(' ','.*'));
  // console.log(filter);
  let dd_tags=document.getElementById("dd_tags")
  for (let a of dd_tags.getElementsByTagName("a")) {
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

function init_tags_dropdown(values) {
  let dd_html=$('#dd_tags')[0]
    for (const val of values)
    {
        var a = document.createElement("a");
        // option.value = val;
        a.innerHTML = val;
        a.href = '#'+a.innerHTML;
        a.addEventListener("mouseup",()=>{addRow_tagTable(val)})
        dd_html.appendChild(a);
    }
  }

// ----------------------------------------
// FUNCTIONS FOR LIST OF TAGS TABLE
function pop_listTags_up() {
  document.getElementById('popup_listTags').style.display='block'
  document.getElementById('popup_listTags').style.zIndex=10
  // retrieve the list of tags
  let listtags=extract_listTags_from_html_table()
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
  }
  update_dd_enveloppe()
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

//# ########################
//#      INITIALIZATION    #
//# ########################
$.when(
  $.get('init',function(data) {
    data=JSON.parse(data)
    // console.log(data);
    // console.log(data['initalTags']);
    // INITIALIZATION of myDropdown menus
    init_dropdown(id='dd_resMethod',values=data['rsMethods'])
    init_dropdown(id='dd_style',values=data['styles'])
    init_dropdown(id='dd_categorie',values=['no categorie'].concat(data['categories']))
    init_tags_dropdown(values=data['all_tags'])
    init_radioButton(id='legend_para',values=['unvisible','tag','description'],'legend')
    $('input[type=radio][name=legend]').change(function() {
      update_legend(this.value)
    })
    // DEFAULT VALUES FOR REQUEST_PARAMETERS
    data['tags'].map(tag=>addRow_tagTable(tag) )
    $('#dd_resMethod')[0].value='mean';
    $('#legend_tag')[0].checked=true;
    $('#in_time_res')[0].value=data['rs']
    $('.title_fig')[0].value=data['fig_name']
    document.getElementsByName('time_window')[0].value=data['time_window']
    document.title=data['title'] +':'+$('.title_fig')[0].value

    $(update_timerange_picker())

    // DEFAULT REAL-TIME
    let refresh_time=document.getElementsByName('in_refresh_time')[0]
    refresh_time.value=DEFAULT_TIME_REFRESH_VALUE
    refresh_time.min=MIN_REFRESH_TIME
    REALTIME_CHECK.checked=false;
    //BUILD THE INITIAL FIGURE
    fetch_figure()
    // data2excel()
  }),
)

//# ########################
//#    REAL TIME FEATURES  #
//# ########################
function update_timerange_picker() {
  let time_window=parseInt(document.getElementsByName('time_window')[0].value)
  $('input[name="datetimes"]').daterangepicker({
    timePicker: true,
    timePicker24Hour:true,
    timePickerSeconds:true,
    startDate: moment().startOf('second').subtract(time_window,'minute'),
    endDate: moment().startOf('second'),
    maxDate:moment().startOf('second'),
    locale: {
      monthNamesShort: ['Janv.', 'Févr.', 'Mars', 'Avril', 'Mai', 'Juin', 'Juil.', 'Août', 'Sept.', 'Oct.', 'Nov.', 'Déc.'],
      // format: 'd-MMM-YY HH:mm',
      monthNames: ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Aout","Septembre","Octobre","Novembre","Decembre"],

      format: 'D MMMM,YYYY HH:mm:ss'
    }
  });
};

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
var listpop_ids=['popup_listTags',"dd_tags","pop_version_info","pop_equations"]
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
