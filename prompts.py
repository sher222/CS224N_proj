import json
import random

# Load the JSON file
with open('data.json', 'r') as f:
    data = json.load(f)

# Extract the word and definition as one string
word_defs = []
for entry in data:
    word = entry['word']
    definition = entry['definition']
    word_def = f"{word}: {definition}"
    word_defs.append(word_def)

# Create the evaluation system
for word_def in word_defs:
    # Extract the example sentences for the word
    for entry in data:
        if entry['word'] == word_def.split(':')[0]:
            example = entry['example']
            break
    examples = example.split('\n')
    # Remove the word in question from the example sentences
    for i, ex in enumerate(examples):
        examples[i] = ex.replace(word_def.split(':')[0], '_________')
    # Choose 5 random words from the JSON file
    choices = random.sample([entry['word'] for entry in data if entry['word'] != word_def.split(':')[0]], 5)
    choices.append(word_def.split(':')[0])
    random.shuffle(choices)
    # Display the evaluation question
    print(f"Fill in the blank:\n{examples[0]}\nChoices: {choices}\n")