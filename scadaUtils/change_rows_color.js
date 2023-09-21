var rowss = document.getElementsByTagName('tr');

  for (let i = 1; i < rowss.length; i++) {
    const row = rowss[i];
    // const colors = ['#df678e', '#7eadd7', 'grey', '#7ed77f'];
    const colors = ['white','#df678e', '#7eadd7', '#f7e6cf', '#7ed77f'];
    const colorIndex = i % colors.length;
    row.style.backgroundColor = colors[colorIndex];
  }
