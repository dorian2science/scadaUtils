function initialisation(data){
    data = JSON.parse(data)
    // ------- INITIALIZATION of myDropdown menus --------
    init_dropdown('dd_models',values=data['models'],change_model)
    $('#dd_models')[0].value = data['model']
    $('#dd_models')[0].dispatchEvent(new CustomEvent("change",{bubbles: true,detail:true}));
    data['tags'].map(tag => addRow_tagTable(tag))
    init_dropdown('dd_resMethod',values=data['rsMethods'])
    init_dropdown('dd_style',values=data['styles'])
    // init_dropdown('dd_operation',values=['no operation'].concat(['derivative','integral','regression p1','regression p2','regression p3']))
    init_radioButton(id='legend_para',values=['unvisible','tag','description'],'legend')
    $('input[type=radio][name=legend]').change(function() {
      update_legend(this.value)
    })
    //--------- DEFAULT VALUES FOR REQUEST_PARAMETERS ------------
    $('#dd_resMethod')[0].value = 'mean'
    $('#dd_time_unit')[0].value = 'S'
    $('#in_time_res')[0].value = data['rs_number']
    $('#gap_switch')[0].checked = false
    $('#legend_tag')[0].checked = true;
    $('.title_fig')[0].value = data['fig_name']

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
    document.getElementById('dd_categorie').value = 'no categorie'
    $('#select_dd_x')[0].value = 'Time'
}

$.when(
  $.get('init',function(data){
    initialisation(data)
  })
)