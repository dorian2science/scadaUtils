var DATETIMEPICKER
var TABLE_TAGS
var TIME_REFRESH_COUNTER = 0;
var REAL_TIME = false
const MIN_REFRESH_TIME = 0
const DEFAULT_TIME_REFRESH_VALUE = 50
const PAPER_BG_COLOR_RT = '#929dbf'
const LIST_DISTINCT_COLORS = get_all_colors()
var converter = new showdown.Converter()


function get_all_colors(){
    return     ['#636EFA',
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
}
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
    console.log(tab_btn_name);
    document.getElementById(tab_btn_name).classList.add("active");
    document.getElementById(tabName).style.display = "block";
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


var all_done = [0,0,0,0]
function load_html_content() {
    return new Promise((resolve, reject) => {
        path_log_version='../static/lib/log_versions.md'
        $.get(path_log_version, function(md_text) {
            $('#pop_version_info')[0].innerHTML=converter.makeHtml(md_text)
            console.log('version_features logger is fully loaded.');
            all_done[0]=1
        })

        $('#tab_display').load('../static/lib/display_panel.html', function() {
            document.getElementById('grid_x').addEventListener('click',modify_grid)
            document.getElementById('grid_y').addEventListener('click',modify_grid)
            document.getElementById('grid_box').addEventListener('click',modify_grid)
            document.getElementById('zeroline').addEventListener('click',modify_grid)

            document.getElementById('grid_x').checked = true
            document.getElementById('grid_y').checked = true
            document.getElementById('grid_box').checked = true
            document.getElementById('zeroline').checked = true
            document.getElementById('gap_switch').checked = false
            all_done[1]=1
            console.log('tab_display is fully loaded.');
        })

        $('#tab_processing').load('../static/lib/processing_panel.html', function() {
            console.log('tab_processing is fully loaded.');
            all_done[2]=1
        })

        $('#tab_dataParameters').load('../static/lib/datasetParameters_panel.html', function() {
            // This callback is executed when the HTML content is fully loaded into the '#div' element
            $('#div_time_resolution').load('../static/lib/time_res_div.html', function() {
                // document.getElementById('check_coarse').checked = true
                $('#select_dd_x')[0].value = 'Time'
                $('#dd_time_unit')[0].value = 'S'
                all_done[3] = 1
                console.log('tab_parameters is fully loaded.');
                resolve()
            });
        })
        // while (!all_done.every(e => e === 1)){
            // }
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


function initialisation(data){
    load_html_content().then(()=>{
        data = JSON.parse(data)
        document.title = data['title'] +':'+$('.title_fig')[0].value
        document.querySelector('.tab-button.active').click()

        // ------- INITIALIZATION of myDropdown menus --------
        // init_dropdown('dd_models',values=data['models'],change_data_set)
        init_dropdown('dd_resMethod',values=data['rsMethods'])
        init_dropdown('dd_style',values=['default','lines+markers','markers','lines','stairs'])
        // init_dropdown('dd_operation',values=['no operation'].concat(['derivative','integral','regression p1','regression p2','regression p3']))
        init_radioButton(id='legend_para',values=['unvisible','tag','description'],'legend')
        $('input[type=radio][name=legend]').change(function() {
            update_legend(this.value)
        })
        init_dropdown('select_dd_x',values=['Time'])
        //--------- DEFAULT VALUES FOR REQUEST_PARAMETERS ------------
        $('#in_time_res')[0].value = data['rs_number']
        $('#dd_time_unit')[0].value = data['rs_unit']
        $('.title_fig')[0].value = data['initial_figname']
        $('#legend_tag')[0].checked = true;
        $('#check_times')[0].checked = true;
        $('#dd_resMethod')[0].value = data['initial_resampling_method']
        //--------  LISTENERS to hide menus when clicking outside of them ----
        // var listpop_ids=["pop_version_info","pop_indicators","bg_color_picker","trace_color_picker","dd_x","dd_y"]
        var listpop_ids = ['popup_listTags',"dd_x","dd_y","pop_version_info","pop_indicators","bg_color_picker","trace_color_picker"]
        add_mouse_up_to_undisplay(listpop_ids)
        
        load_drag_drop_upload()
        get_sessions().then(()=>{
            console.log(data['initial_session']);
            $('#dd_session')[0].value = data['initial_session']
            update_data_sets().then(()=>{
                change_dataSet()
            })
        })
        DATETIMEPICKER = document.getElementById('datetimepicker')
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
        TABLE_TAGS = document.getElementById('table_tags')
        AColorPicker.from('#bg_color_picker',{'hueBarSize':[width-60,50],'slBarSize':[width,150]})
            .on('change', (picker, color) => {
                hex_color_value=AColorPicker.parseColor(color, "hex");
                console.log('bg');
                Plotly.relayout('plotly_fig', {'plot_bgcolor':color})
            })

        AColorPicker.from('#trace_color_picker',{'hueBarSize':[width-60,50],'slBarSize':[width,150]})
            .on('change', (picker, color) => {
                hex_color_value = AColorPicker.parseColor(color, "hex");
                update = {
                    'line.color':hex_color_value,
                    'marker.color':hex_color_value,
                }
                Plotly.restyle('plotly_fig', update, CURTRACE);
                btn = Array.from(TABLE_TAGS.children[0].children).slice(1,).filter(x=>x.children[1].textContent == fig.data[CURTRACE].name)[0].children[2].children[0]
                btn.style.backgroundColor = hex_color_value
                btn.value = hex_color_value
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
}

$.when(
  $.get('init',function(data){
    initialisation(data)
  })
)
