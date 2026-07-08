// JobPilot AU — CV template (Australian conventions: no photo, no DOB).
// Input: data.json = {name, contact_line, sections: [{title, units: [{text}]}]}

#let data = json("data.json")

#set page(paper: "a4", margin: (x: 1.7cm, top: 1.5cm, bottom: 1.5cm))
#set text(size: 10pt)
#set par(justify: false, leading: 0.5em)
#set list(tight: true, spacing: 0.45em, indent: 0.4em)

// ---- Header -----------------------------------------------------------
#align(center)[
  #text(size: 17pt, weight: "bold")[#data.at("name", default: "")]
  #if data.at("contact_line", default: "") != "" [
    #v(0.15em)
    #text(size: 9pt, fill: rgb("#444444"))[#data.at("contact_line", default: "")]
  ]
]
#v(0.2em)
#line(length: 100%, stroke: 0.7pt)

// ---- Sections ---------------------------------------------------------
#for section in data.at("sections", default: ()) [
  #v(0.55em)
  #text(size: 11pt, weight: "bold")[#upper(section.title)]
  #v(-0.35em)
  #line(length: 100%, stroke: 0.4pt + rgb("#999999"))
  #v(0.1em)
  #for unit in section.at("units", default: ()) [
    - #unit.text
  ]
]
