import json
import os.path

with open(os.path.abspath('./options_data.json'), 'r') as file:
	data = json.load(file)

d = {}
for opt, data in data.items():
	if 'outputs' in data.keys():
		for out in data['outputs']:
			try:
				d[out].append(opt)
			except KeyError:
				d[out] = [opt]
print d