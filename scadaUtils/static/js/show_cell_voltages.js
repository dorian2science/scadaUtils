function waitForPlotly_fig() {
    const myElement = document.getElementById('plotly_fig');
    if (myElement) {
        in_greenlight = document.createElement('input')
        in_greenlight.id = 'in_greenlight'
        in_greenlight.type = 'checkbox'
        lab_greenlight = document.createElement('label')
        lab_greenlight.textContent = 'greenlight'
        in_greenlight.checked = false
        in_greenlight.addEventListener('change',load_green_light)
        list_buttons_request.appendChild(in_greenlight)
        list_buttons_request.appendChild(lab_greenlight)
        in_datetime = document.createElement('input')
        in_datetime.id = 'in_dt_cells'
        in_datetime.type = 'range'
        in_datetime.min = 0
        in_datetime.step = 1
        in_datetime.value = 0
        in_datetime.max = 1
        in_datetime.addEventListener('input',update_cells_graph_and_summary)

        div_bar_graph = document.createElement('div')
        div_bar_graph.id = 'div_bar_graph'
        div_summary = document.createElement('div')
        div_summary.id = 'div_summary'
        div_sum = document.createElement('div')

        figs_div = plotly_fig.parentElement
        figs_div.style.display='inline-flex'
        div1 = document.createElement('div')
        div1.style.display='inline-block'
        div1.appendChild(document.getElementsByClassName('title_fig')[0])
        div1.appendChild(in_datetime)
        div1.appendChild(plotly_fig)

        figs_div.appendChild(div1)
        figs_div.appendChild(div_summary)
        figs_div.appendChild(div_bar_graph)
        
        clearInterval(interval);
    }
  }
const interval = setInterval(waitForPlotly_fig, 100); // Check every 100 milliseconds


function load_green_light(){
    if (in_greenlight.checked){
        in_datetime.style.display='inline-block'
        div_summary.style.display='inline-block'
        div_bar_graph.style.display='inline-block'
        btn_update.addEventListener('click',get_data_stack)
        
        btn_width.addEventListener('input',update_size_figures_greenlight)
        btn_height.addEventListener('input',update_size_figures_greenlight)
        btn_width.removeEventListener('input',update_size_figure)
        btn_height.removeEventListener('input',update_size_figure)
    }else{
        div_summary.style.display='none'
        div_bar_graph.style.display='none'
        in_datetime.style.display='none'
        btn_update.removeEventListener('click',get_data_stack)
        btn_width.addEventListener('input',update_size_figure)
        btn_height.addEventListener('input',update_size_figure)
        btn_width.removeEventListener('input',update_size_figures_greenlight)
        btn_height.removeEventListener('input',update_size_figures_greenlight)
    }
}
    
    
var GREENLIGHT_DATA 
function get_data_stack(){
    lab_greenlight.textContent = 'Waiting for data'
    lab_greenlight.style.backgroundColor = 'orange'

    let parameters = build_request_parameters()
    LAST_REQUEST = JSON.stringify(parameters)
    console.log("sending request to get greenlight data");
    $.post('/greenlight_data',LAST_REQUEST,function(res,status){
        // threat the notification message sent by the backend
        var notif = res['notif']
        // console.log(notif);
        lab_greenlight.textContent = 'greenlight'
        lab_greenlight.style.backgroundColor = ''
    
        GREENLIGHT_DATA = res
        if ( notif!=200){
            alert(notif)
        }
        console.log('greenlight data received');
        update_range_datetime_cells()
        in_datetime.value = Math.floor(in_datetime.max/2)
        initialize_summary_table()
        update_cells_graph_and_summary()
        btn_height.dispatchEvent(new Event('input')) 
        btn_width.dispatchEvent(new Event('input')) 
    })
}

function update_range_datetime_cells(){
    in_dt_cells.max = GREENLIGHT_DATA['Time'].length
    in_dt_cells.style.width = btn_width.value+"px"
}

function initialize_summary_table() {
    const table = document.createElement('table');
    // Optionally, add some basic styling
    table.style.backgroundColor = 'white';
    table.style.whiteSpace = "nowrap";
    table.style.textAlign = "left";
    table.setAttribute('border', '1');
  
    // Create header row
    const headerRow = table.insertRow();
    const headerCell1 = headerRow.insertCell();
    headerCell1.innerHTML = "<strong>Tag</strong>";
    const headerCell2 = headerRow.insertCell();
    headerCell2.innerHTML = "<strong>Value</strong>";
    const headerCell3 = headerRow.insertCell();
    headerCell3.innerHTML = "<strong>Unit</strong>";
  
    summary = GREENLIGHT_DATA['tags_diag_units']
    for (const key of GREENLIGHT_DATA["real_order"]) {
        const row = table.insertRow();
        const keyCell = row.insertCell();
        keyCell.textContent = key;
        const valueCell = row.insertCell();
        valueCell.id = 'row_summary_'+key;
        valueCell.textContent = 0;
        const unitCell = row.insertCell();
        unitCell.textContent = summary[key];
    }
    div_summary.innerHTML = '';
    div_summary.appendChild(table);
}

function update_bar_graph(){
    idx = in_datetime.value
    a = moment(GREENLIGHT_DATA['Time'][idx])
    time = a.format('ddd, D MMM Y, H')+'h'+a.format('mm:ss') + '.' + a.milliseconds() 
    df_cells = GREENLIGHT_DATA['df_cells']

    cell_ids = Object.keys(GREENLIGHT_DATA['df_cells']).map(x=>x.split('_').slice(-1)[0])
    cell_voltages = Object.keys(df_cells).map(x=>df_cells[x][idx].toFixed(2)) 
    nb_cells = cell_voltages.length

    layout = {
        title: 'Cell voltages:'+time,
        width:800,
        xaxis: {
            title: 'cell id'
        },
        yaxis: {
            title: 'mV',
            range:[-10,1050]
        }
    };
    cells_data = [{
        x: cell_ids,
        y: cell_voltages,
        type: 'bar',
        marker: {
            color: Array.from({ length: nb_cells}, () => 'blue'),
        }
    }];
    Plotly.newPlot('div_bar_graph',cells_data,layout)
}

function update_cells_graph_and_summary(){
    update_bar_graph()
    // update_summary_values
    idx = in_datetime.value
    stack_data = quick_extraction(GREENLIGHT_DATA['df_stack'],idx,2)
    for (const key in stack_data) {
        valueCell = document.getElementById('row_summary_'+key)
        valueCell.textContent = stack_data[key];
    }    

    layout = {
        shapes: [
          {
            type: 'line',
            x0: GREENLIGHT_DATA['Time'][idx],
            x1: GREENLIGHT_DATA['Time'][idx],
            y0: fig.layout['yaxis111']['range'][0],
            y1: fig.layout['yaxis111']['range'][1],
            line: {
              color: 'black',
              width: 4,
              dash:'dot'
            }
          }
        ],
      };

    Plotly.relayout('plotly_fig',layout)
}

function update_size_figures_greenlight(){
    layout = {}
    e = btn_width
    layout['width'] = e.value
    document.getElementsByClassName('title_fig')[0].style.width = e.value+'px'
    in_dt_cells.style.width = e.value+'px'
    e = btn_height
    layout['height'] = e.value
    div_summary.children[0].style.height=e.value+"px" 
    Plotly.relayout('div_bar_graph', layout)
    Plotly.relayout('plotly_fig', layout)
    Plotly.relayout('div_bar_graph', layout)
}

