import json
import numpy as np
# read the file into a string
with open('../data/words.json', 'r') as f:
    data = f.read()

# fix the format of the string for the first 10 entries
fixed_data = []
counter = 0
for line in data.splitlines():
    if counter >= 100:
        break
    fixed_data.append(json.loads(line))
    print(counter)
    counter += 1

# write the fixed data to a file with newlines between each object
with open('tunedWords.json', 'w') as f:
    json.dump(fixed_data, f, separators=(',', ':'))

with open('tunedWords.json', 'r') as infile:
    data = json.load(infile)

with open('../data/finalWords.json', 'w') as outfile:
    # Write each object on its own line, separated by commas
    outfile.write('[')
    for i, obj in enumerate(data):
        if i == 0:
            # Write the first object without a comma
            outfile.write(json.dumps(obj))
        else:
            # Write subsequent objects with a leading comma
            outfile.write(',' + json.dumps(obj))
        # Add a newline character to the end of each object
        outfile.write('\n')
    outfile.write(']')
