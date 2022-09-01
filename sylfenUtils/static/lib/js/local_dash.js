var COOL
var converter = new showdown.Converter()
$.when(
  $.get('logVersion_smallPower.md', function(md_text) {
    $('#pop_version_info')[0].innerHTML=converter.makeHtml(md_text)
  }),
)
