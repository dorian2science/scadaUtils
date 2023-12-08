var DATETIMEPICKER
var TIME_REFRESH_COUNTER = 0;
var REAL_TIME = false
const MIN_REFRESH_TIME = 0
const DEFAULT_TIME_REFRESH_VALUE = 50
const PAPER_BG_COLOR_RT = '#929dbf'
var LIST_DISTINCT_COLORS
var LIST_ORIGINAL_COLORS = []
var STABLE_PARAMETERS_PANEL=true
var TIMES = []
var FIG
DIS_FACTOR = 0
DELTAT = 'seconds'
var CONFIG = {
  showEditInChartStudio: false,
  locale: 'fr',
  displaylogo: false,
  plotlyServerURL: "https://chart-studio.plotly.com",
  editable:false,
  modeBarButtonsToRemove: ['select2d','lasso2d'],
  modeBarButtonsToAdd: ['toggleSpikelines','lasso2d','toggleHover','hoverclosest','hovercompare'],
}

function get_all_colors(){
    file = '../static/colors.json'
    fetch(file)
        .then(response => response.json())
        .then(data => {
            LIST_DISTINCT_COLORS = data;
        })
        .catch(error => {
            console.error('Error:', error);
        });
}
get_all_colors()

function showTab(tabName) {
    var i, tabContent, tabButton;

    tabContent = document.getElementsByClassName("tab-content");
    for (i = 0; i < tabContent.length; i++) {
        tabContent[i].style.display = "none";
    }

    tabButton = document.getElementsByClassName("tab-button");
    for (i = 0; i < tabButton.length; i++) {
        tabButton[i].classList.remove("active");
    }
    tab_btn_name = "btn_"+tabName
    // console.log(tab_btn_name);
    document.getElementById(tab_btn_name).classList.add("active");
    document.getElementById(tabName).style.display = "block";
    switch_tab_dataset()
}

function switch_tab_dataset(){
    if (document.getElementById('btn_tab_dataset').classList.contains('active')){
        div_resMethod_dataset.appendChild(dd_resMethod)
        div_datetimepicker_dataset.appendChild(datetimepicker)
        div_time_res_dataset.appendChild(in_time_res)
        div_time_res_dataset.appendChild(dd_time_unit)
        div_tags_dataset.appendChild(in_dd_y)
        div_tags_dataset.appendChild(dd_y)
        div_tags_dataset.appendChild(btn_add_tags)
        list_buttons_request_dataset.appendChild(btn_update)
        list_buttons_request_dataset.appendChild(btn_export)
        list_buttons_request_dataset.appendChild(btn_fig)        
        update_data_sets().then(()=>{
            change_dataSet()
        })

    }else if(document.getElementById('btn_tab_parameters').classList.contains('active')){
        div_resMethod.appendChild(dd_resMethod)
        div_datetimepicker.appendChild(datetimepicker)
        div_time_res.appendChild(in_time_res)
        div_time_res.appendChild(dd_time_unit)
        div_tags.appendChild(in_dd_y)
        div_tags.appendChild(dd_y)
        div_tags.appendChild(btn_add_tags)
        list_buttons_request.appendChild(btn_update)
        list_buttons_request.appendChild(btn_export)
        list_buttons_request.appendChild(btn_fig)
        change_model()
    }
}

function add_mouse_up_to_undisplay(listpop_ids){
    document.addEventListener("mouseup", function(event) {
        for (id of listpop_ids) {
            var html_obj = document.getElementById(id);
            // console.log(id,html_obj);
            if (html_obj){
                if (!html_obj.contains(event.target)) {
                    html_obj.style.display='none'
                    html_obj.style.zIndex=-1
                }

            }
        }
        });
}

function load_html_content() {
    return new Promise((resolve, reject) => {
        $('#tab_display').load('../static/html/display_panel.html', function() {
            document.getElementById('grid_x').addEventListener('click',modify_grid)
            document.getElementById('grid_y').addEventListener('click',modify_grid)
            document.getElementById('grid_box').addEventListener('click',modify_grid)
            document.getElementById('zeroline').addEventListener('click',modify_grid)

            document.getElementById('grid_x').checked = true
            document.getElementById('grid_y').checked = true
            document.getElementById('grid_box').checked = true
            document.getElementById('zeroline').checked = true
            document.getElementById('gap_switch').checked = false
            console.log('tab_display is fully loaded.');
        })

        $('#tab_processing').load('../static/html/processing_panel.html', function() {
            console.log('tab_processing is fully loaded.');
        })

        $('#tab_god_mode').load('../static/html/god_mode.html', function() {
            console.log('tab_god_mode is fully loaded.');
        })
        
        $('#tab_datasetParameters').load("../static/html/datasetParameters_panel.html", function() {
            console.log('tab_datasetParameters is fully loaded.');
            $('#tab_dataParameters').load("../static/html/dataParameters_panel.html", function() {
                console.log('tab_dataParameters is fully loaded.');
                $('#div_time_res').load("../static/html/time_res_div.html", function() {
                    console.log('div_time_res is fully loaded.');
                    resolve()
                })
            })
        })
    })
}
    
function load_drag_drop_upload(){
    
    const dropArea = document.getElementById("drop-area");
    const fileInput = document.getElementById("file-input");
    const fileList = document.getElementById("file-list");
    
    // Prevent default behavior to open file on drop
    dropArea.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropArea.classList.add("highlight");
    });
    
    dropArea.addEventListener("dragleave", () => {
        dropArea.classList.remove("highlight");
    });
    
    dropArea.addEventListener("drop", (e) => {
        e.preventDefault();
        dropArea.classList.remove("highlight");
        const files = e.dataTransfer.files;
        handleFiles(files);
    });
    
    fileInput.addEventListener("change", () => {
        const files = fileInput.files;
        handleFiles(files);
    });
    
    function handleFiles(files) {
        for (const file of files) {
            const listItem = document.createElement("li");
            listItem.textContent = file.name + ' is being processed.';
            fileList.appendChild(listItem);
            fileList.appendChild(listItem);
            send_file(file)
        }
    }
}

function send_file(file) {
    // Send the file to the server using FormData and XMLHttpRequest
    const formData = new FormData();
    formData.append('file', file);
    
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload', true);
    
    xhr.onload = function(filename) {
        if (xhr.status === 200) {
            console.log('File uploaded successfully');
            alert('your file has been  processed and is available in the dataset drop down menu.')
            document.getElementById("file-list").innerHTML = "";
            update_data_sets()
        } else {
            console.error('Error uploading file');
        }
    };
    xhr.send(formData);
}

var INIT_DATA
$.get('init',function(data){
    load_html_content().then(()=>{
        data = JSON.parse(data)
        INIT_DATA = data
        document.title = data['title'] +':'+$('.title_fig')[0].value
        img_logo.src = data["logo_path"]
        document.querySelector('link[rel="icon"]').href = data["logo_path"]
        document.getElementById("help-me-link").href = data["helpmelink"]
        $.get(data["log_version_file"], function(md_text) {
            converter = new showdown.Converter()
            $('#pop_version_info')[0].innerHTML=converter.makeHtml(md_text)
            console.log('version_features logger is fully loaded.');
        })
        
        document.querySelector('.tab-button.active').click()
        // ------- INITIALIZATION of myDropdown menus --------
        init_dropdown('dd_models',values=data['models'],change_model)
        init_dropdown('dd_resMethod',values=data['rsMethods'])
        init_dropdown('dd_style',values=['default','lines+markers','markers','lines','stairs'])
        // init_dropdown('dd_operation',values=['no operation'].concat(['derivative','integral','regression p1','regression p2','regression p3']))
        init_radioButton(id='legend_para',values=['unvisible','tag','description'],'legend')
        $('input[type=radio][name=legend]').change(function() {
            update_legend(this.value)
        })
        init_dropdown('select_dd_x',values=['Time'])
        //--------- DEFAULT VALUES FOR REQUEST_PARAMETERS ------------
        $('#select_dd_x')[0].value = 'Time'
        $('#dd_time_unit')[0].value = 'S'
        $('#in_time_res')[0].value = data['rs_number']
        $('#dd_time_unit')[0].value = data['rs_unit']
        $('.title_fig')[0].value = data['initial_figname']
        document.title = data['initial_figname']
        $('#legend_tag')[0].checked = true;
        $('#check_times')[0].checked = true;
        $('#dd_resMethod')[0].value = data['initial_resampling_method']
        $('#dd_models')[0].value = data['initial_model']

        //--------  LISTENERS to hide menus when clicking outside of them ----
        var listpop_ids = ['popup_listTags',"dd_x","dd_y","pop_version_info","pop_indicators","bg_color_picker","trace_color_picker"]
        add_mouse_up_to_undisplay(listpop_ids)
        
        // ----------- more initialisations ------- 
        load_drag_drop_upload()
        get_sessions().then(()=>{
            $('#dd_session')[0].value = data['initial_session']
            update_data_sets().then(()=>{
                change_dataSet()
            })
        })

        change_model()
        INITIAL_TIMEWINDOW = data['initial_time_window']/60
        $('#datetimepicker').daterangepicker({
            timePicker: true,
            timePicker24Hour:true,
            timePickerSeconds:true,
            showDropdowns:true,
            locale: {
              monthNamesShort: ['Janv.', 'Févr.', 'Mars', 'Avril', 'Mai', 'Juin', 'Juil.', 'Août', 'Sept.', 'Oct.', 'Nov.', 'Déc.'],
              monthNames: ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Aout","Septembre","Octobre","Novembre","Decembre"],
              format: 'D MMM YYYY HH:mm:ss',
            }
            })
            AColorPicker.from('#bg_color_picker',{'hueBarSize':[width-60,50],'slBarSize':[width,150]})
            .on('change', (picker, color) => {
                hex_color_value=AColorPicker.parseColor(color, "hex");
                console.log('bg');
                Plotly.relayout('plotly_fig', {'plot_bgcolor':color})
            })
            
        loc_table = get_active_table()
        AColorPicker.from('#trace_color_picker',{'hueBarSize':[width-60,50],'slBarSize':[width,150]})
            .on('change', (picker, color) => {
                hex_color_value = AColorPicker.parseColor(color, "hex");
                update = {
                    'line.color':hex_color_value,
                    'marker.color':hex_color_value,
                }
                cur_btn_color.style.backgroundColor = hex_color_value
                cur_btn_color.value = hex_color_value
                cur_name = cur_btn_color.parentElement.parentElement.children[1].textContent 
                if (typeof fig !== 'undefined'){
                    cur_trace_index = fig.data.map(x=>x.name).indexOf(cur_name)
                    Plotly.restyle('plotly_fig', update, cur_trace_index);
                }
            });

        //# add SHORTCUTS  #
        document.getElementById('plotly_fig').onkeyup=function(e){
            // document.onkeyup=function(e){
            // console.log('shortcut triggered');
            if (e.key == 't') {$('#legend_tag')[0].checked=true;update_legend($('input[name="legend"]')[0].value)}
            else if (e.key == 'd') {$('#legend_description')[0].checked=true;update_legend($('input[name="legend"]')[0].value)}
            else if (e.key == 'u') {$('#legend_unvisible')[0].checked=true;update_legend($('input[name="legend"]')[0].value)}
        }
    })
})
