import json
import numpy as np
import os
# read the file into a string
with open('../data/words.json', 'r') as f:
    data = f.read()

# fix the format of the string for the first 10 entries
fixed_data = []
counter = 0
for line in data.splitlines():
    if counter >= 20000:
        break
    
    obj = json.loads(line)
    # filter out words that contain more than one word
    contains_digit = False
    if ' ' not in obj['word']:

        for char in obj['word']:
            if char.isdigit():
                contains_digit = True
                break
        for char in obj['definition']:
            if char.isdigit():
                contains_digit = True
                break
        for char in obj['example']:
            if char.isdigit():
                contains_digit = True
                break
        if not contains_digit:
            # remove the specified attributes from each object in the fixed_data list
            for attr in ['permalink', 'thumbs_up', 'author', 'defid', 'current_vote', 'thumbs_down', 'tags', 'sounds', 'lowercase_word', '_id']:
                del obj[attr]
            # remove extra quotation marks from the example attribute
            obj['example'] = obj['example'].replace('"', '')
            # replace newline and tab characters with a space in all attributes
            for key, value in obj.items():
                obj[key] = value.replace('\n', ' ').replace('\t', ' ').replace('\r', ' ')
            for key, value in obj.items():
                obj[key] = value.replace('  ', ' ')
            fixed_data.append(obj)
    print(counter)
    counter += 1

# write the fixed data to a file with newlines between each object
with open('tunedWords.json', 'w') as f:
    json.dump(fixed_data, f, separators=(',', ':'))

with open('tunedWords.json', 'r') as infile:
    data = json.load(infile)

# write the modified data to a new file without the removed attributes
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

os.remove('tunedWords.json')
