## Prepare venv

- install requirements
- enable venv

## Prepare files

For each questionnaire, three files are needed: 

- an export from an OmegaT project containing the file (argument `--omt`)
- the translation file including the locale-based filtering properties (argument `--xml`)
- the MoM file (argument `--mom`)

### Prepare XLS file `--omt {q}_OMT.xlsx` 

You'll need a PISA25 team project containing the two QQ batches `04_QQS_N` and `05_QQA_N`. Alternatively you can always add the two batch folders later manually.

1. Pack the team project (any `pisa_2025ft_translation_*`) to create an offline package.
2. Unpack that project
3. Add QQ batch folders containing the XML file to the project (if necessary)
4. In the project settings, remove tags and disable segmentation
5. If that wasn't done already, remove ITS filtering props in every XML file -- see below
6. Export the project as Excel
7. In the export, remove all sheets (if any) except the one for the questionnaire in question
8. In the one remaining sheet, remove the trailing `_0` in the "segment ID" column (or remove "name = " in the "comment" column), so as to have the raw key without the `_0` suffix that the XML filter adds (for whatever reason)
9. Remove the title row and all columns except the source text and the key
10. Name those two columns as 'label' and 'key'
11. Save as xlsx.

#### Remove ITS filtering properties in the XML files used for the XLS export:

- Using a copy of the XML file, remove all text matched by ` its:(localeFilterList|localeFilterType)="[^"]+"` so that it is locale-neutral and nothing is filtered out. Do not modify the original XML file (used in argument `--xml`).

## Run the script

TIP: For convenient, name the three files as follows (for, say, `TCQ`): `TCQ.xml`, `TCQ_OMT.xlsx` and `TCQ_MOM.xlsx`.

Put the QQ abbreviation in variable `q` and run the script like this (example using `PAQ`):

```
q="PAQ"
python validate_mom_text_based.py --omt $(pwd)/${q}_OMT.xlsx --xml $(pwd)/${q}.xml --mom $(pwd)/${q}_MOM.xlsx
```
