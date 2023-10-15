## Prepare venv
- install requirements
- enable venv

## Prepare files

### Prepare file `{q}_OMT.xlsx` 

- remove tags and disable segmentation in OmegaT project
- remove its filtering props in XML file
- export as excel
- in the export, remove all sheets except the one for the q in question
- in the remaining sheet, remove the title row and all columns except the source text and the key
- name those two columns as 'label' and 'key'
- remove the trailing _0 in the segment ID (or remove "name = " in the commnt column)
- save as xlsx

### Remove 

## Run

 q="PAQ" && python validate_mom_text_based.py --omt $(pwd)/${q}_OMT.xlsx --xml $(pwd)/${q}.xml --mom $(pwd)/${q}_MOM.xlsx
