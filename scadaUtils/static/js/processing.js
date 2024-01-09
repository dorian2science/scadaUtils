
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

function add_variable(new_var_name,formula,unit){
  if (list_vars_table().includes(new_var_name)){
    alert('the variable : '+ new_var_name + 'already exists. Please select a new name and recompute the variable.')
    return 
  }

  varRegex = /v\d+/g;
  listtags = Object.keys(DATA['data'])

  // Replace variables with values from the array x
  new_var = []
  for(k=0;k<DATA['data'][listtags[0]].length;k++){
    replace_formula = formula.replace(varRegex, (match) => {
      index = parseInt(match.slice(1));
      if (index >= 1 && index <= listtags.length) {
        return DATA['data'][listtags[[index - 1]]][k]
      } else {
        throw new Error(`Index ${index} is out of bounds for array x`);
      }
    });
    new_var.push(eval(replace_formula));
  }

  new_trace = {
    x: DATA['Time'],
    y: new_var,
    name: new_var_name,
    tag:new_var_name,
    type:"scattergl",
    yaxis:"y111",
    marker:{color:'black'},
  }
  Plotly.addTraces('plotly_fig', new_trace)
  .then(()=>{
    build_layout_from_planch()
  })
  update_size_markers()
  addRow_varTable(new_var_name,formula,unit)
  add_row_trace_table(new_var_name,'black',unit,1,1)
  // $('#dd_style')[0].dispatchEvent(new CustomEvent("change",{bubbles: true}));
}
function add_formula_variable(){
  new_var_name = document.getElementById('new_var_name').value
  formula = in_formula.value
  unit = in_formula_unit.value
  add_variable(new_var_name,formula,unit)
}

function update_dd_tag_for_formula() {
  dd_tags_formula = $('#dd_var')[0]
  dd_tags_formula.innerHTML=''
  // listtags = Object.keys(DATA['data']).concat(Object.keys(GREENLIGHT_DATA['df_cells']),Object.keys(GREENLIGHT_DATA['df_stack']))
  listtags = Object.keys(DATA['data'])
  listtags = listtags.map((x,k)=>'v'+(k+1)+':'+x) 
  init_dropdown('dd_var', listtags)
}

function list_vars_table(){
  return Array.from(table_computed_vars.children[0].children).slice(1,).map(x=>x.children[1].textContent)
}

function addRow_varTable(tagname,formula,unit) {
  list_tags = Array.from(table_computed_vars.children[0].children).slice(1,).map(x=>x.children[1].textContent)
  if (!list_tags.includes(tagname)) {
    var row = table_computed_vars.insertRow(table_computed_vars.rows.length);
    row.insertCell(0).innerHTML = '<input type="button" class="btn_delete" value = "X" onClick="deleteVariable(this)">';
    row.insertCell(1).innerHTML = tagname;
    replace_formula = formula.replace(varRegex, (match) => {
      index = parseInt(match.slice(1));
      if (index >= 1 && index <= listtags.length) {
        return listtags[[index - 1]]
      } else {
        throw new Error(`Index ${index} is out of bounds for array x`);
      }
    });
    row.insertCell(2).innerHTML = replace_formula;
    row.insertCell(3).textContent = unit;
  }
}

function deleteVariable(e){
  row = e.parentElement.parentElement
  tag = row.children[1].textContent
  console.log(tag);
  idx = fig.data.map(x=>x.tag).indexOf(tag)
  console.log(idx);
  if (idx!=-1){
    Plotly.deleteTraces(fig,idx);
    tt = table_traces.children[0]
    idx2 = Array.from(tt.rows).map(x=>x.children[0].textContent).indexOf(tag)
    tt.removeChild(tt.children[idx2]) 
    row.parentElement.removeChild(row)
    DATA[tag]
  }
}

function delete_all_vars(){
  rows = Array.from(table_computed_vars.rows).slice(1,)
  for (k=0;k<rows.length;k++){
    console.log(rows[k]);
    rows[k].children[0].children[0].click()
  }
}

function browse_variables_file(){
  fileVarsInput.click();
}

function load_table_variables(){
    file = fileVarsInput.files[0];
    console.log(file);
    const JSON_READER = new FileReader();
    data_tags = Array.from(Object.keys(DATA['data'])).map((v, k) => ({ [v]: 'v'+(k +1)})).reduce((acc, obj) => ({ ...acc, ...obj }), {})
    
    JSON_READER.onload = function(event) {
      try {
        table_vars_dict = JSON.parse(event.target.result);
        delete_all_vars()
        for (new_var_name in table_vars_dict){
          formula = table_vars_dict[new_var_name]['formula']
          unit = table_vars_dict[new_var_name]['unit']
          // replace the tags in the formula by their variables as they appear in the dropdown menu.
          for (tag in data_tags){
            pattern = new RegExp(tag, "g");
            formula = formula.replace(pattern,data_tags[tag])
            console.log(tag);
            console.log(formula);
          }
          add_variable(new_var_name,formula,unit)
        }
      } catch (error) {
        console.log(error);
        msg = 'Votre tableau de variables ne semble pas être compatible ou ne pas respecter le format attendu.'
        msg += '\nLes formules que vous essayez de charger sont les suivantes :\n'
        msg += Object.values(table_vars_dict).map(x=>x['formula']).join('\n')
        msg += "\nAssurez vous d'avoir chargé tous les tags puis recharger votre tableau de variables."
        alert(msg)
      }
    };
    JSON_READER.readAsText(file);
}

function save_table_variables(){
  table_vars_dict = {}
  rows = Array.from(table_computed_vars.rows).slice(1,)
  for (k=0;k<rows.length;k++){
    table_vars_dict[rows[k].children[1].textContent]={
      "formula" : rows[k].children[2].textContent,
      "unit" : rows[k].children[3].textContent
    }
      }
  download_json(table_vars_dict,'table_variables.json')
}