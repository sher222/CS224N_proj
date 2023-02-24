# coding=utf-8
# Copyright 2018 The Google AI Language Team Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
r"""Creates the set of fake new words, their scores, and their morphology.

The pre-specified command line arguments are those that are used in WinoDict
(https://arxiv.org/abs/2209.12153). This can be used 'as is' with the provided
morphology rules, or a different file can be provided.

Note that the exact words used in the paper won't be generated due to some
standardizations around e.g., the random seed and the word list used.

pip install nltk

python create_new_words.py --output_path=$HOME/test_output.tsv

"""
import collections
import dataclasses
from typing import Dict, Set

from absl import app
from absl import flags
import nltk
from nltk import corpus
from nltk import lm

# import english_words

_N = flags.DEFINE_integer("n", 3,
                          "Number of characters in the probabilistic model.")

_SEED = flags.DEFINE_integer(
    "seed", 1, "Random seed. If unchanged, output will"
    "be deterministic")

_MIN_SCORE = flags.DEFINE_float("min_score", -30.0,
                                "Min score of generated words.")

_MAX_LENGTH = flags.DEFINE_integer("max_length", 12,
                                   "Max length to use for word generation.")

_MIN_LENGTH = flags.DEFINE_integer("min_length", 5,
                                   "Max length to use for word generation.")

_NUM_ITERATIONS = flags.DEFINE_integer(
    "num_iterations", 3000,
    "Approximate number of examples to generate. Depending on bucketing and "
    "filters, could end up being less.")

_NUM_BUCKETS = flags.DEFINE_integer(
    "num_buckets", 5, "Number of score buckets to use, sorting words from more "
    "to less probable. Max number of examples per bucket will be the number "
    "of iterations divided by the number of buckets.")

_OUTPUT_PATH = flags.DEFINE_string(
    "output_path", None, "Where to write the generated words.", required=True)

_PATH_TO_MORPH_RULES = flags.DEFINE_string(
    "morph_rules_path", "morph_rules.txt",
    "Path to the set of morphology rules. Should be included in current "
    "directory. They can also be generated by create_morph_rules.py given "
    "an input set.")


@dataclasses.dataclass
class ScoredNGram:
  word: str
  score: float

  def __str__(self):
    return f"{self.word}\t{self.score:.5f}"


@dataclasses.dataclass
class ScoredMorphedNGram:
  scored_ngram: ScoredNGram
  morphology: Dict[str, str]

  def __str__(self):
    morph_part = ",".join(
        f"{pos}:{morphed}" for (pos, morphed) in self.morphology.items())
    return f"{self.scored_ngram}\t{morph_part}"


def _build_all_examples(lexicon):
  return [list(word) for word in lexicon if word.islower()]


def _train_ngram_model(n, lexicon):
  exs = _build_all_examples(lexicon)
  train, vocab = lm.preprocessing.padded_everygram_pipeline(n, exs)
  model = lm.MLE(n)
  model.fit(train, vocab)
  return model


def _prettyprint_ngrams(output):
  return "".join(c for c in output if "<" not in c)


class NGramGenerator:
  """Uses a three-letter ngram model and MLE to create/score new words.

  _model: a MLE model trained on n-letter sequences found in the
    vocabulary of english words.
  _ngram_size: The length of sequences. A higher value will give more
    english-looking words.
  _lexicon: The set of english words from which to train the model.
  """
  _model: lm.MLE
  _ngram_size: int
  _lexicon: Set[str]

  def __init__(self, ngram_size, lexicon):
    self._ngram_size = ngram_size
    self._model = _train_ngram_model(ngram_size, lexicon)
    self._lexicon = lexicon

  def score_word(self, word):
    """Scores a word as the sum of its n-letter sequences."""
    max_n = min(len(word), self._ngram_size)
    chars = ["<s>"] + list(word) + ["</s>"]
    score = 0
    for i in range(1, len(word)):
      context_start = max(0, i - max_n + 1)
      context = chars[context_start:i]
      new_score = self._model.logscore(chars[i], context)
      score += new_score

    return score

  def make_word(self, max_length, seed = None):
    return _prettyprint_ngrams(
        self._model.generate(max_length, random_seed=seed))

  def make_scored_ngram(self,
                        max_length,
                        seed = None):
    word = self.make_word(max_length, seed)
    score = self.score_word(word)
    return ScoredNGram(word, score)

  def validate_scored_ngram(self, scored_ngram, min_score,
                            min_length):
    """Checks if the generated word follows all requirements on length and score.

    Note that the word also should not be an existing word.

    Args:
      scored_ngram: The scored new word to check.
      min_score: Minimum allowed score for the new word.
      min_length: Minimum allowed length for the new word.

    Returns:
      True if the word follows all requirements, false otherwise.
    """
    if scored_ngram.word in self._lexicon:
      return False
    elif len(scored_ngram.word) < min_length:
      return False
    elif scored_ngram.score == float("-inf"):
      return False
    elif scored_ngram.score < min_score:
      return False
    return True


def _get_bucket(scored_ngram, min_score,
                num_buckets):
  # Note that the max score is implicitly 0, so -min_score is equivalent to
  # max_score - min_score.
  valid_score_range = -min_score
  bucket_score_range = valid_score_range / num_buckets
  return int(-scored_ngram.score // bucket_score_range)


def generate_ngram_examples(model,
                            min_length,
                            max_length,
                            num_buckets,
                            min_score,
                            num_iterations,
                            random_seed = 1):
  """Generates a sorted list of scored new words based on the requirements.

  Args:
    model: Trained model to create and score words.
    min_length: The minimum length of which to create new words.
    max_length: The maximum length of which to create new words.
    num_buckets: The number of buckets from which to stratify the scoring.
    min_score: The minimum allowed score. Note that each bucket will then be an
      equal range between 0 and this value.
    num_iterations: The number of initial examples to be created. Note that many
      of the examples will be filtered, depending on the other arguments and
      others will be subsampled via the buckets. In general, specify this to be
      larger than the number of examples needed.
    random_seed: Random seed of the process to multiply by.

  Returns:
    A list of scored words following the above requirements.
  """
  score_buckets = collections.defaultdict(list)
  word_set = set()
  for i in range(num_iterations):
    scored_ngram = model.make_scored_ngram(max_length, seed=i * random_seed)
    if scored_ngram.word in word_set:
      continue
    word_set.add(scored_ngram.word)
    if model.validate_scored_ngram(scored_ngram, min_score, min_length):
      bucket = _get_bucket(scored_ngram, min_score, num_buckets)
      score_buckets[bucket].append(scored_ngram)

  final = []
  max_examples_per_bucket = num_iterations // num_buckets
  for ngram_score_list in score_buckets.values():
    final.extend(ngram_score_list[:max_examples_per_bucket])
  return sorted(final, key=lambda sn: -sn.score)


def add_morphology_to_examples(
    examples,
    morph_rules):
  """Adds morphology to generated words based on the provided rules.

  Args:
    examples: List of input words and scores.
    morph_rules: Set of rules to edit words based on part of speech and suffix
      substitution.

  Returns:
    List of words with a dictionary of part of speech to conjugated word form
      added.
  """
  morphed_examples = []
  for example in examples:
    if (morphology := _morph_by_rules(example.word, morph_rules)) is not None:
      morphed_examples.append(ScoredMorphedNGram(example, morphology))
  return morphed_examples


def _morph_by_rules(
    word, morph_rules):
  """Creates the morphology dictionary for a word based on the rules.

  Note that this dictionary is from a part of speech to that word's conjugation
  for that part of speech. It tries to find the longest matching suffix in the
  dictionary, failing if a suffix isn't found for some part of speech.

  Args:
    word: The word to find the morphology for.
    morph_rules: The part of speech to suffix substitution dictionary.

  Returns:
    A part of speech to conjugated word dictionary.
  """
  morphs = {}
  for pos, suffix_to_change in morph_rules.items():
    i = max(5, len(word))
    morph = None
    while i >= 2:
      suggested_suffix = word[-i:]
      if suggested_suffix in suffix_to_change:
        morph = f"{word[:-i]}{suffix_to_change[suggested_suffix]}"
        break
      i -= 1
    if morph is None:
      return None
    morphs[pos] = morph
  return morphs


def read_morph_rules(file_path):
  """Reads the suffix substitution rules from the file.

  Note that the file can be edited manually or created from scratch by a
  different process, but it should be included in the package.

  Args:
    file_path: Path to file containing the morphology rules in the following
      format - PART_OF_SPEECH(SUFFIX1:SUBSTITION1,...,SUFFIX_N:SUBSTITUTION_N)

  Returns:
    Dictionary of part of speech to a dictionary of suffix substitutions
  """
  pos_to_morph_rules = {}
  with open(file_path) as fr:
    for line in fr:
      if not line.strip():
        continue
      pos, morphs = line.split("(")
      morphs = morphs[:-1]  # Remove trailing final paren
      pos_to_morph_rules[pos] = dict(
          suffix_pair.split(":")
          for suffix_pair in morphs.split(",")
          if "'" not in suffix_pair)
  return pos_to_morph_rules


def main(argv):
  if len(argv) > 1:
    raise app.UsageError("Too many command-line arguments.")
  nltk.download("words")
  generator = NGramGenerator(_N.value, set(corpus.words.words()))
  print("Finished training model with nltk vocab.")
  examples = generate_ngram_examples(generator, _MIN_LENGTH.value,
                                     _MAX_LENGTH.value, _NUM_BUCKETS.value,
                                     _MIN_SCORE.value, _NUM_ITERATIONS.value,
                                     _SEED.value)
  print(f"Generated {len(examples)} initial examples.")
  print(f"Reading morphology from {_PATH_TO_MORPH_RULES.value}")
  morph_rules = read_morph_rules(_PATH_TO_MORPH_RULES.value)
  morphed_examples = add_morphology_to_examples(examples, morph_rules)
  print(f"Successfully created {len(morphed_examples)} final examples")
  with open(_OUTPUT_PATH.value, "wt") as fw:
    fw.writelines(f"{ex}\n" for ex in morphed_examples)
  print(f"Wrote to {_OUTPUT_PATH.value}")


if __name__ == "__main__":
  app.run(main)
