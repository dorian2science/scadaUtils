function linspace(start,stop,nb){
  return Array.from({ length: nb }, (_, index) => start + (index / (nb - 1)) * (stop - start));
}

function arange(start,stop,step){
  return Array.from({ length: Math.ceil((stop - start) / step) }, (_, index) => start + index * step);
}

function formatNumber(number) {
  formats = {
      0:'',
      1:'k',
      2:'m',
      3:'G',
      4:'T',
      5:'P',
  }
  nums = number.toString().split('.')
  mag = formats[Math.floor((nums[0].length-1)/3)]
  bigDigit = Math.floor(nums[0].length%3)

  if ((mag=='')){
      x1 = nums[0]
      x2 = nums[1].slice(0,3-nums[0].length)
  }else{
      x1 = nums[0].slice(0,bigDigit)
      x2 = nums[0].slice(bigDigit,3)
  }
  if(bigDigit!=0){
      return x1+ '.' + x2 + mag
  }else{
    if (mag==''){
      return x1 + mag
    }else{
      return x2+mag
    }
  }
}

function divide_interval(nbs,s,maxi){
  p = (maxi-s)/nbs-s
  intervals = []
  for (k=0;k<nbs;k++){
    intervals.push([s + k *(s + p), s+ k *(s + p)+p])
  }
  return intervals
}

function download_json(obj){
  const blob = new Blob([JSON.stringify(obj)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'obj.json';
  a.click();
  URL.revokeObjectURL(url);
}

function saturates(nb,mini,maxi){
  nb = Math.min(nb,maxi)
  return Math.max(nb,mini)
}

function save_my_request_parameters() {
  const blob = new Blob([JSON.stringify(build_request_parameters())], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'gui_params.json';
  a.click();
  URL.revokeObjectURL(url);
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


function empty_table(table){
  nbrows = table.rows.length
  for (let index=1;index<nbrows;index++){
    table.deleteRow(1)
  }
}


function quick_extraction(obj,idx,precision){
  return Object.keys(obj).reduce((result, key) => {
    result[key] = obj[key][idx].toFixed(precision)
    return result
  },{});
}

