import os, sys
import polars as pl
import pprint
import regex as re
import pandas as pd
from xml.dom.minidom import parse, parseString
from deepdiff import DeepDiff
from dotted_dict import DottedDict
import time
import argparse

print(sys.prefix)


""" preconditions: 
- all item nodes have id attribute
- all label nodes have key attributes
- all label nodes have a parent item
- all item nodes have at least one label child
"""


# ############# PROGRAM DESCRIPTION ###########################################

text = "Check MoM-based ITS filter properties in XML file"

# initialize arg parser with a description
parser = argparse.ArgumentParser(description=text)
parser.add_argument("-V", "--version", help="show program version", action="store_true")
#parser.add_argument("-p", "--params", help="specify path to list of patterns")
parser.add_argument(
    "-o", "--omt", help="specify path to the OmegaT export containing labels without segmentation and without tags")
parser.add_argument(
    "-m", "--mom", help="specify path to the MoM config spreadsheet")
parser.add_argument(
    "-x", "--xml", help="specify path to the XML translation file containing the ITS filter props")

# read arguments from the command cur_str
args = parser.parse_args()

# check for -V or --version
version_text = "Check MoM filter props 1.0"
if args.version:
    print(version_text)
    sys.exit()

if args.omt and args.mom and args.xml:
    omt_fpath = args.omt.strip()
    mom_fpath = args.mom.strip()
    xml_fpath = args.xml.strip()
else:
    print("Some required argument not found. Run this script with `--help` for details.")
    sys.exit()

parent_dir = os.path.dirname(os.path.realpath(__file__))
log_dpath = os.path.join(parent_dir, "_log")
os.makedirs(log_dpath, exist_ok=True)
log_file = os.path.join(log_dpath, "log.txt") # @todo: add timestamp to log file


# ############# FUNCTIONS ###########################################

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

# [re.split(r'_[a-z0-9]{32}', id)[0] if id != None else "N/A" for id in omt_data["key"].to_list()]
def get_label_id(item_id, label_key):
	""" Remove hash from label key, and optionally remove item id. """ 
	if item_id not in label_key:
		print(f"The label key {label_key} is not a child of the item id {item_id}!")
		return None

	# adding optional Q01TA to account for anomaly ST001Q01TA
	# if re.search(r"^ST\d{3}$", item_id):
	# 	pattern = re.compile(fr'^{item_id}_{item_id}[^_]*')
	# elif re.search(r"^ST\d{3}[A-Z]{3}$", item_id):
	# 	# national ids, e.g. ST828DEU
	# 	pattern = re.compile(fr'^{item_id}_{item_id[:-3]}[^_]*')

	pattern = re.compile(r'^([^_]+)(?:[A-Z]{3})?_\1.+')
	match = re.search(pattern, label_key)
	if match:
		# strip hash
		# label_id = re.sub(r"_\w{32}_\d{1,2}$", "", label_key).removeprefix(f"{item_id}_")
		label_id =   re.split(r'_[a-z0-9]{32}', label_key.removeprefix(f"{item_id}_"))[0]
		          
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


def set_label_id_count(label_id, source):
	id_count = 1 if label_id not in id_counter[source] else id_counter[source][label_id]+1
	return id_count


def make_label_id_unique(label_id, label_text, origin):
	if mom_label_ids.count(label_id) > 1:
		if label_text != None and label_text != "" and not re.search(r"^\s+$", label_text):
			id_string_concat = f"{label_id}@{label_text.strip()}"
			if origin == "MoM":
				mom_id_string_concats.append(id_string_concat)
				return id_string_concat
			elif origin == "XML" and id_string_concat in mom_id_string_concats:
				return id_string_concat
			elif origin == "XML" and any(re.match(rf"{x.replace('@', '.+?')}", id_string_concat) for x in mom_id_string_concats):
				return next(x for x in mom_id_string_concats if re.match(rf"{x.replace('@', '.+?')}", id_string_concat))
			else:
				print(f"> {id_string_concat=} is NOT in MoM")
		return label_id
	return label_id
			

def is_in_master(item_id):
 	return 'fr-ZZ' in mom[item_id]["include"]		


def included_in_mom(item_id, locale):
 	return locale in mom[item_id]["include"]		



# constants

today = time.strftime("%Y%m%d-%H%M%S")

id_counter = {}
id_counter["mom"] = {}
id_counter["xml"] = {}

output = f'mom_mismatches_report_{today}.xlsx'
filter_id = None # "ST229" # "ST003" # "ST801NZL" # None # "ST228" # "ST828"

xml_file = "STQ.xml"
omt_file = "STQ_itemID_sourceText_allKeys_noMrkp_noSegm.xlsx"
xls_file = "MoM.xlsx" # _ST229.xlsx" # _ST003.xlsx" # _ST801NZL.xlsx" # _ST228.xlsx"
# xls_file = "MoM_ST841.xlsx"
# xls_file = "MoM_ST001.xlsx"




# process MoM (Excel)

# print("==== PROCESSING MOM DATA ====")
mom = DottedDict()
mom_data = pl.read_excel(mom_fpath)

locales = [x for x in mom_data.columns if is_locale(x)]

mom_label_ids = mom_data["ITEM ID"].to_list()
mom_id_string_concats = []



for row in mom_data.rows(named=True):
	# include_dict = {key: value for (key, value) in row if condition(key, value)}
	label_id = row["ITEM ID"]
	label_text = row["Text For MoM"]

	if filter_id and label_id and filter_id not in label_id: continue # filter test

	# print(f"{label_text=}")

	# mom: label_id='ST828_05DEU'
	# mom: label_id='ST828C01HADEU'

	# use the first definition of item properties, use for all labels with same id
	# id_counter['mom'][label_id] = 1 if label_id not in id_counter['mom'] else id_counter['mom'][label_id]+1
	# id_counter['mom'][label_id] = set_label_id_count(label_id, source = "mom")

	# label_id_unique = f"{label_id}_{str(id_counter['mom'][label_id])}"
	label_id_unique = make_label_id_unique(label_id, label_text, origin = "MoM")

	# print(f"mom: {label_id_unique=}")
	if label_id_unique not in mom:
		# what todo? if value is None?
		mom[label_id_unique] = {
			'include': [key for key, value in row.items() if value != None and "Y" in value and is_locale(key)], 
			'exclude': [key for key, value in row.items() if value != None and "N" in value and is_locale(key)]
		}
		# todo: move none, "", etc to func is_valid()

# todo: inherit from the item level (or find discrepancies)

# process XML and OMT export

# print(mom_id_string_concats)

# print("==== PROCESSING OMT DATA ====")

print(f"Open {mom_fpath=}")
omt_data = pd.read_excel(omt_fpath)

# print(omt_data.to_dict('records'))
# print(f"{omt_data=}")
# omt_data_dict = dict(zip(omt_data.key, omt_data.label))
omt_data_dict = {str(k).removesuffix("_0"):v for (k,v) in dict(zip(omt_data.key, omt_data.label)).items() if str(k) != ""}
# pprint.pprint(omt_data_dict)
# remove \u200c

# omt_data['label_id'] = [re.split(r'_[a-z0-9]{32}', id)[0] if id != None else "N/A" for id in omt_data["key"].to_list()]
# and re.search('_[a-z0-9]{32}', id) 
omt_data['label_id'] = [re.split(r'_[a-z0-9]{32}', id)[0] if isinstance(id, str) else "N/A" for id in omt_data["key"].to_list()]


# add _# to each item_id

# add its filter props to omt_data

# if if item_id matches
# elif text matches and label_id is in mom's item id
# elif ???

# print("==== PROCESSING XML DATA ====")

print(f"{mom_id_string_concats=}")

print(f"Open {xml_fpath=}")
xml_data = DottedDict()
document = parse(xml_fpath)
labels = document.getElementsByTagName("label")
for label in labels:
	# if label has its props, take those
	# else, take item's
	item_id = label.parentNode.getAttribute("id")
	label_key = label.getAttribute("key")
	label_id = get_label_id(item_id, label_key)
	# print(f"{item_id=} + {label_id=} = {label_key=}")

	# what if label_id is None???

	# if item_id != filter_id: continue # filter test
	if filter_id and label_id and filter_id not in label_id: continue # filter test

	# get label_text
	if label_key in omt_data_dict:
		label_text = str(omt_data_dict[label_key]).removeprefix("\u200c").removesuffix("\u200c")
	else:
		print(f"Label key {label_key} not found in omt data")
		label_text = None

	# get item's (parent's) filtering properties if label does not have them
	if node_has_filter_props(label):
		label_filter_props = get_filter_props(label)
	elif node_has_filter_props(label.parentNode):
		label_filter_props = get_filter_props(label.parentNode)
	else:
		print(f"No filter props found for label {label_id}!")

	# id_counter['xml'][label_id] = 1 if label_id not in id_counter['xml'] else id_counter['xml'][label_id]+1
	id_counter['xml'][label_id] = set_label_id_count(label_id, source = "xml")

	# label_id_unique = f"{label_id}_{str(id_counter['xml'][label_id])}"
	label_id_unique = make_label_id_unique(label_id, label_text, origin = "XML")

	# print(f"xml: {label_id_unique=}")
	if label_id_unique not in xml_data:
		xml_data[label_id_unique] = label_filter_props



if mom != xml_data:
	print(f"Mismatches found, report written to '{output}'.")
	# take include or exclude depending on what is in the XML, remove the inverted list
	diff = DeepDiff(mom, xml_data)
	# pprint.pprint(f"{diff=}")
	report = get_report_from_diff(diff)
	#pprint.pprint(f"{report['labels']=}")

	# headers that diff uses
	headers = ['Label ID', 'Filter type expected', 'Position', 'Locale', 'Property in XML']
	dirty_labels = [dict(zip(headers, label)) for label in report['labels']]

	filtered_labels = [
		{k: v for k, v in d.items() if k != 'Position'} for d in dirty_labels 
		if (included_in_mom(d['Label ID'], d['Locale']) and d['Filter type expected'] == "include")
		or (not included_in_mom(d['Label ID'], d['Locale']) and d['Filter type expected'] == "exclude")
		]

	# create dataframes
	df_labels = pd.DataFrame(filtered_labels, columns = [h for h in headers if h != 'Position'])
	df_items = pd.DataFrame(report["items"], columns = ['Label ID', 'Property in XML'])

	with pd.ExcelWriter(output) as writer:  
		df_labels.to_excel(writer, sheet_name='labels', index = False)
		df_items.to_excel(writer, sheet_name='items', index = False)
else:
	print("No differences found")
	if os.path.exists(output): os.remove(output)

# todo:

# find duplicate IDs where two or more do not have label

#print(f"{mom_id_string_concats=}")
#print(f"{mom_label_ids=}")

mom_id_string_concats_dict = {} # x.split("@")[0]: [] for x in mom_id_string_concats}
for x in mom_id_string_concats:
	if x.split("@")[0] not in mom_id_string_concats_dict:
		mom_id_string_concats_dict[x.split("@")[0]] = []
	mom_id_string_concats_dict[x.split("@")[0]].append(x.split("@")[1])
#pprint.pprint(f"{mom_id_string_concats_dict=}")

for id in mom_id_string_concats_dict.keys():
	y = len(id)
	if y > mom_label_ids.count(x):
		print(f"more occurrences of {id} than labels associated with it")
