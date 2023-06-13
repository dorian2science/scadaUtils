color_hex=Array.from(document.getElementsByTagName('td')).filter(x=>x.innerHTML.includes('#'))
color_hex.map(x=> x.parentElement.children[5].style.backgroundColor=x.innerHTML)
