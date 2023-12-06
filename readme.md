## Prepare venv

- install requirements
- enable venv

## Prepare files

For each questionnaire, three files are needed: 

- an export from an OmegaT project containing the file (argument `--omt`)
- the translation file without filtering properties (argument `--xml`)
- the MoM file (argument `--mom`)

### Prepare file `--xml {q}.xml` 

Remove ITS filtering properties:

- Using a copy of the XML file, remove all text matched by ` its:(localeFilterList|localeFilterType)="[^"]+"` so that it is locale-neutral and nothing is filtered out.

### Prepare file `--omt {q}_OMT.xlsx` 

You'll need a PISA25 team project containing the two QQ batches `04_QQS_N` and `05_QQA_N`. Alternatively you can always add the two batch folders later manually.

1. Pack the team project (any `pisa_2025ft_translation_*`) to create an offline package.
2. Unpack that project
3. Add QQ batch folders containing the XML file to the project (if necessary) -- see above
4. In the project settings, remove tags and disable segmentation
5. If that wasn't done already, remove ITS filtering props in XML file -- see above
6. Export the project as Excel
7. In the export, remove all sheets (if any) except the one for the questionnaire in question
8. In the one remaining sheet, remove the title row and all columns except the source text and the key
9. Name those two columns as 'label' and 'key'
10. Remove the trailing `_0` in the segment ID (or remove "name = " in the comment column).
11. Save as xlsx.

## Run the script

Put the QQ abbreviation in variable `q` and run the script like this (example using `PAQ`):

```
q="PAQ"
python validate_mom_text_based.py --omt $(pwd)/${q}_OMT.xlsx --xml $(pwd)/${q}.xml --mom $(pwd)/${q}_MOM.xlsx
```
