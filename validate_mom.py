import os, sys
import polars as pl
import pprint
import regex as re
import pandas as pd
from xml.dom.minidom import parse, parseString
from deepdiff import DeepDiff
from dotted_dict import DottedDict

""" preconditions: 
- all item nodes have id attribute
- all label nodes have key attributes
- all label nodes have a parent item
- all item nodes have at least one label child
"""

def is_locale(key):
	bcp47_regex = r"^[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-[A-Z]{2}|-[0-9]{3})(?:(?:-x)?-[a-z0-9]{5,8})?$"
	if re.match(bcp47_regex, key):
		return True


def node_has_filter_props(label):
	if label.getAttribute("its:localeFilterType") and label.getAttribute("its:localeFilterList"):
		return True


def get_filter_props(node):
	filter_type = node.getAttribute("its:localeFilterType")
	filter_list = node.getAttribute("its:localeFilterList").split(",")
	inverted_filter_list = [l for l in locales if l not in filter_list]
	inverted_filter_type = "include" if filter_type == "exclude" else "exclude"
	# node.getAttribute("its:localeFilterType"): node.getAttribute("its:localeFilterList").split(",")
	return {filter_type: filter_list, inverted_filter_type: inverted_filter_list}


def get_label_id(item_id, label_key):
	""" Remove hash from label key, and optionally remove item id. """ 
	if item_id not in label_key:
		print(f"The label key {label_key} is not a child of the item id {item_id}!")
		return None
	
	# adding optional Q01TA to account for anomaly ST001Q01TA
	if re.search(r"^ST\d{3}(Q01TA)?$", item_id):
		pattern = re.compile(fr'^{item_id}_{item_id}[^_]*')
	elif re.search(r"^ST\d{3}[A-Z]{3}$", item_id):
		# national ids, e.g. ST828DEU
		pattern = re.compile(fr'^{item_id}_{item_id[:-3]}[^_]*')

	match = re.search(pattern, label_key)
	if match:
		# strip hash
		label_id = re.sub(r"_\w{32}_\d{1,2}$", "", label_key).removeprefix(f"{item_id}_")
		# label_id = match.group().split(f"{item_id}_", 1)[1]
		return label_id
	else:
		return item_id # label id is the same as item id


def merge_filter_props(item_locale_filter_type, item_locale_filter_list, label_locale_filter_type, label_locale_filter_list):
	if item_locale_filter_type == label_locale_filter_type:
		return {label_locale_filter_type: label_locale_filter_list}
	else:
		return {item_locale_filter_type: item_locale_filter_list, label_locale_filter_type: label_locale_filter_list}


def get_report_from_diff(diff):
	report = {}
	report["items"] = []
	report["labels"] = []

	for key, data in diff.items():
		error = key.split("_")[-1] # added or removed
		if "dictionary_item_" in key:
			# todo: add label mismatches this to another sheet
			for value in data:
				fields = re.findall(r"\['?([^\]]+?)'?\]", value)
				report["items"].append([*fields, error])
			continue # do something with this! #@dev
		elif "iterable_item_" in key:
			for details, locale in data.items():
				fields = re.findall(r"\['?([^\]]+?)'?\]", details)
				report["labels"].append([*fields, locale, error])
	return report



mom = DottedDict()
ids = {}
ids["mom"] = {}
ids["xml"] = {}

output = 'mom_mismatches_report.xlsx'
filter_id = None # "ST228" # "ST828"
xls = "MoM.xlsx" # _ST228.xlsx"
# xls = "MoM_ST841.xlsx"
# xls = "MoM_ST001.xlsx"
mom_data = pl.read_excel(xls)
locales = [x for x in mom_data.columns if is_locale(x)]
for row in mom_data.rows(named=True):
	# include_dict = {key: value for (key, value) in row if condition(key, value)}
	label_id = row['International Item ID']
	
	if filter_id and label_id and filter_id not in label_id: continue # filter test

	# mom: label_id='ST828_05DEU'
	# mom: label_id='ST828C01HADEU'

	# use the first definition of item properties, use for all labels with same id
	ids['mom'][label_id] = 1 if label_id not in ids['mom'] else ids['mom'][label_id]+1
	label_id_unique = f"{label_id}_{str(ids['mom'][label_id])}"
	print(f"mom: {label_id_unique=}")
	if label_id_unique not in mom:
		# what todo? if value is None?
		mom[label_id_unique] = {
			'include': [key for key, value in row.items() if value != None and "Y" in value and is_locale(key)], 
			'exclude': [key for key, value in row.items() if value != None and "N" in value and is_locale(key)]
		}
# todo: inherit from the item level (or find discrepancies)

xml = DottedDict()
document = parse("STQ.xml")
labels = document.getElementsByTagName("label")

for label in labels:
	# if label has its props, take those
	# else, take item's
	item_id = label.parentNode.getAttribute("id")
	label_key = label.getAttribute("key")
	label_id = get_label_id(item_id, label_key)

	# if item_id != filter_id: continue # filter test
	if filter_id and label_id and filter_id not in label_id: continue # filter test


	# get item's (parent's) filtering properties if label does not have them
	if node_has_filter_props(label):
		label_filter_props = get_filter_props(label)
	elif node_has_filter_props(label.parentNode):
		label_filter_props = get_filter_props(label.parentNode)
	else:
		print(f"No filter props found for label {label_id}!")

	ids['xml'][label_id] = 1 if label_id not in ids['xml'] else ids['xml'][label_id]+1
	label_id_unique = f"{label_id}_{str(ids['xml'][label_id])}"
	print(f"xml: {label_id_unique=}")
	if label_id_unique not in xml:
		xml[label_id_unique] = label_filter_props


if mom != xml:
	print(f"Mismatches found, report written to '{output}'.")
	# take include or exclude depending on what is in the XML, remove the inverted list
	diff = DeepDiff(mom, xml)
	# print(f"{diff=}")
	report = get_report_from_diff(diff)
	# print(f"{report=}")
	# sys.exit()

	# create dataframes
	df_labels = pd.DataFrame(report["labels"], columns = ['Label ID', 'Filter type', 'Position', 'Locale', 'Mismatch type'])
	df_items = pd.DataFrame(report["items"], columns = ['Label ID', 'Mismatch type'])

	with pd.ExcelWriter(output) as writer:  
		df_labels.to_excel(writer, sheet_name='labels', index = False)
		df_items.to_excel(writer, sheet_name='items', index = False)
else:
	print("No differences found")
	if os.path.exists(output): os.remove(output)
	

# if Y or N missing = same as master
# Y and N strip() 
# find values in MoM that are not Y or N: 
# N81:z: ST430_1	include	10	en-GB-scotland	added
# DR85, DS85

# cs-CZ: BD511, 512. MmM: N, XML <item id="ST006"> Y
# BD539
# DR146, DS146 : empty
# BS368, BT368, DQ368
# BP2506 -> fixed

# add cell coordinate?
# remove position

# checks: all cells with same label ID should ahve the same value

# ST250Q21DA vi-VN	fr-SN
