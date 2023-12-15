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