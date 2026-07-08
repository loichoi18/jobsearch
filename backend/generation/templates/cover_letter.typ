// JobPilot AU — cover letter template.
// Input: data.json = {name, contact_line, recipient_line, paragraphs: [text]}

#let data = json("data.json")

#set page(paper: "a4", margin: (x: 2.2cm, top: 2cm, bottom: 2cm))
#set text(size: 10.5pt)
#set par(justify: false, leading: 0.65em)

#text(size: 14pt, weight: "bold")[#data.at("name", default: "")]
#if data.at("contact_line", default: "") != "" [
  #v(0.1em)
  #text(size: 9pt, fill: rgb("#444444"))[#data.at("contact_line", default: "")]
]
#v(0.3em)
#line(length: 100%, stroke: 0.6pt)
#v(1em)

#if data.at("recipient_line", default: "") != "" [
  #data.at("recipient_line", default: "")
  #v(0.6em)
]

#for paragraph in data.at("paragraphs", default: ()) [
  #paragraph
  #v(0.6em)
]

#v(0.4em)
Kind regards, \
#data.at("name", default: "")
