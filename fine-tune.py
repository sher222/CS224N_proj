import torch
from transformers import GPT2Tokenizer, GPT2LMHeadModel

# Load pre-trained GPT-2 model and tokenizer
model_name = 'gpt2'
model = GPT2LMHeadModel.from_pretrained(model_name)
tokenizer = GPT2Tokenizer.from_pretrained(model_name)

# Tokenize corpus of definitions
corpus = ['word1: definition1', 'word2: definition2', 'newword: newdefinition']
tokenized_corpus = [tokenizer.encode(text) for text in corpus]

# Extract token embeddings
all_embeddings = model.transformer.wte.weight.data
new_word_embeddings = []

# Split tokenized corpus into sequences of fixed length
seq_length = 32
for sequence in tokenized_corpus:
    for i in range(0, len(sequence), seq_length):
        input_seq = sequence[i:i+seq_length]
        
        # Check if new word is present in the sequence
        if 'newword' in tokenizer.decode(input_seq):
            # Initialize new word embedding as average of other token embeddings
            other_tokens = [token for token in input_seq if token != tokenizer.pad_token_id and token != tokenizer.eos_token_id and token != tokenizer.bos_token_id and token != tokenizer.unk_token_id and token != tokenizer.sep_token_id and token != tokenizer.cls_token_id and token != tokenizer.mask_token_id and token != tokenizer.convert_tokens_to_ids('newword')]
            other_embeddings = all_embeddings[other_tokens]
            new_word_embedding = torch.mean(other_embeddings, dim=0)
            new_word_embeddings.append(new_word_embedding)

# Update model parameters with new word embeddings
num_new_words = len(new_word_embeddings)
if num_new_words > 0:
    new_embeddings = torch.stack(new_word_embeddings, dim=0)
    params = model.state_dict()
    params['transformer.wte.weight'][-num_new_words:,:] = new_embeddings
    model.load_state_dict(params)

# Fine-tune model on custom corpus of definitions
inputs = torch.tensor(tokenized_corpus)
labels = inputs.clone()
labels[labels == tokenizer.pad_token_id] = -100  # Set padding tokens to ignore loss
optimizer = torch.optim.Adam(model.parameters(), lr=5e-5)
for epoch in range(3):
    loss = 0.0
    for i in range(0, len(inputs), 8):
        inputs_batch = inputs[i:i+8]
        labels_batch = labels[i:i+8]
        model.zero_grad()
        outputs = model(inputs_batch, labels=labels_batch)
        loss_batch = outputs[0]
        loss_batch.backward()
        optimizer.step()
        loss += loss_batch.item()
    print('Epoch: {}, Loss: {:.4f}'.format(epoch, loss))