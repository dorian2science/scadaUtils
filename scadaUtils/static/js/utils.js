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

function divide_interval(nbs,s,max){
  p = (max+s)/nbs-s
  intervals = []
  for (k=0;k<nbs;k++){
    intervals.push([k *(s + p), k *(s + p)+p])
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
