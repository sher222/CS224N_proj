import transformers
import torch

tok = transformers.GPT2Tokenizer.from_pretrained('gpt2')
model = transformers.AutoModelForCausalLM.from_pretrained('gpt2')
tok.add_tokens(['Aragorn', 'Frodo', 'Lothlorien'])
model.resize_token_embeddings(len(tok))



params = model.state_dict()
embeddings = params['transformer.wte.weight']
pre_expansion_embeddings = embeddings[:-3,:]
mu = torch.mean(pre_expansion_embeddings, dim=0)
n = pre_expansion_embeddings.size()[0]
sigma = ((pre_expansion_embeddings - mu).T @ (pre_expansion_embeddings - mu)) / n
dist = torch.distributions.multivariate_normal.MultivariateNormal(
        mu, covariance_matrix=1e-5*sigma)

new_embeddings = torch.stack(tuple((dist.sample() for _ in range(3))), dim=0)
embeddings[-3:,:] = new_embeddings
params['transformer.wte.weight'][-3:,:] = new_embeddings
model.load_state_dict(params)


sent2 = 'Dogs are great because they are '
tok.decode(model.generate(**tok(sent2, return_tensors='pt'), do_sample=True)[0])
"Dogs are great because they are icky and don't tend to get in the way much,"