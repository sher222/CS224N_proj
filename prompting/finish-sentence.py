import json
import random

# Load the JSON file
with open('../data/finalWords.json', 'r') as f:
    data = json.load(f)

# Create the evaluation system
for entry in data:
    # Extract the word and definition for the current entry
    word = entry['word']
    definition = entry['definition']
    # Create the evaluation question
    choices = random.sample([e['word'] for e in data if e['word'] != word], 5)
    choices.append(word)
    random.shuffle(choices)
    question = f"The word that means '{definition}' is __"
    # Display the evaluation question
    print(f"Fill in the blank:\n{question}\nChoices: {choices}\n")