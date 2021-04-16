#!/usr/bin/env python3

import sys
import re
import logging

from itertools import tee
from collections import Counter, defaultdict
from argparse import ArgumentParser


# Argument parser settings
DESCRIPTION = 'Replace unicode replacement characters based on word statistics'
DEFAULT_MIN_PROB = 0.999
DEFAULT_MIN_COUNT = 2


# Regular expressions
TOKENIZATION_RE = re.compile('([^\W\d_]+|�|\d+|\s+|.)')
ALPHA_RE = re.compile('^[^\W\d_]+$')
NON_ASCII_ALPHA_RE = re.compile('[^\W\d_a-zA-Z]')


# Logger setup
logging.basicConfig()
logger = logging.getLogger()
#logger.setLevel(logging.DEBUG)


def argparser():
    ap = ArgumentParser(description=DESCRIPTION)
    ap.add_argument('-c', '--min-count', default=DEFAULT_MIN_COUNT, type=int,
                    help='minimum ngram occurrence count')
    ap.add_argument('-i', '--ignore-irregular', default=False,
                    action='store_true',
                    help='ignore n-grams with irregular capitalization')
    ap.add_argument('-p', '--min-prob', default=DEFAULT_MIN_PROB, type=float,
                    help='minimum conditional probability')
    ap.add_argument('-v', '--verbose', default=False, action='store_true')
    ap.add_argument('ngram_counts')
    ap.add_argument('file', nargs='+')
    return ap


def nonspace_ngram(tokens, idx, n):
    rev_ngram = [tokens[idx]]
    for i in range(idx-1, -1, -1):
        if len(rev_ngram) >= n:
            break
        if tokens[i] and not tokens[i].isspace():
            rev_ngram.append(tokens[i])
    if len(rev_ngram) != n:
        raise ValueError()
    return tuple(reversed(rev_ngram))


def replace_replacement_chars(token, idx, tokens, probs, counts, stats, args):
    if token.isspace() or not token:
        return token    # whitespace or empty, don't count 
    elif '�' not in token:
        return token
    max_n = None
    stats['total'] += 1
    for n in sorted(probs, reverse=True):
        logger.debug(f'n={n}')
        if n > idx:
            continue
        ngram = nonspace_ngram(tokens, idx, n)
        if ngram not in probs[n]:
            logger.debug(f'not found: {ngram}')
            continue
        if max_n is None:
            max_n = n
        if probs[n][ngram][0][1] < args.min_prob:
            logger.debug(f'reject {ngram} by prob: {probs[n][ngram]}')
        elif counts[n][ngram] < args.min_count:
            logger.debug(f'reject {ngram} by count: {counts[n][ngram]}')
        else:
            logger.debug(f'accept {ngram}')
            stats[f'unambiguous (n={n})'] += 1
            return probs[n][ngram][0][0]
    if max_n is None:
        stats['missing'] += 1
    else:
        stats['ambiguous'] += 1
    return token


def is_alpha_or_replacement(token):
    return token == '�' or ALPHA_RE.match(token)


def tokenize(sentence):
    tokens, prev_is_ar = ['<s>'], False
    for t in TOKENIZATION_RE.split(sentence):
        if t:
            is_ar = is_alpha_or_replacement(t)
            if prev_is_ar and is_ar:
                tokens[-1] += t    # combine alpha and replacement
            else:
                tokens.append(t)
            prev_is_ar = is_ar
    tokens.append('</s>')
    return tokens
    

def process_file(fn, probs, counts, stats, args):
    with open(fn) as f:
        for ln, l in enumerate(f, start=1):
            tokens = tokenize(l)
            assert l == ''.join(tokens[1:-1])
            for i in range(len(tokens)):
                tokens[i] = replace_replacement_chars(
                    tokens[i], i, tokens, probs, counts, stats, args)
            print(''.join(tokens[1:-1]), end='')


def pairwise(iterable):
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def has_irregular_capitalization(string):
    # Introduced as generalized filter for double-encoding errors
    # mapping e.g. "työ" -> "tyÃ¶". Currently only checking for
    # lowercase -> uppercase transitions in neighbouring characters.
    for char, next_ in pairwise(string):
        if char.islower() and next_.isupper():
            return True
    return False


def read_ngram_counts(fn, args):
    print(f'Reading ngram counts from {fn} ...', file=sys.stderr)
    counts = defaultdict(Counter)
    total = defaultdict(int)
    with open(fn) as f:
        if f.readline().rstrip('\n') != '\\data\\':
            raise ValueError(f'expected "\\data\\" in {fn}')
        for ln, line in enumerate(f, start=2):
            if line.isspace() or not line:
                break
            try:
                m = re.match(r'^ngram (\d+)=(\d+)$', line)
                assert m
                n, v = [int(i) for i in m.groups()]
                assert v not in total
                total[n] = v
            except:
                raise ValueError(f'failed to parse {fn} line {ln}: {l}')
        while True:
            try:
                line = f.readline().rstrip('\n')
                ln += 1
                if line == '\\end\\':
                    break
                m = re.match(r'^\\(\d+)-grams:$', line)
                n = int(m.group(1))
                assert m
                while True:
                    line = f.readline().rstrip('\n')
                    ln += 1
                    if ln % 1000000 == 0:
                        print(f'Read {ln} lines ...', file=sys.stderr)
                    if line.isspace() or not line:
                        break
                    count, ngram = line.rstrip('\n').split('\t')
                    if (args.ignore_irregular and
                        has_irregular_capitalization(ngram)):
                        logging.debug(f'skip irregular {ngram}')
                        continue
                    count, ngram = int(count), tuple(ngram.split())
                    if count == 1:
                        continue    # TODO!!!
                    assert len(ngram) == n
                    assert ngram not in counts[n]
                    counts[n][ngram] = count
            except:
                raise ValueError(f'failed to parse {fn} line {ln}: {line}')

    total = sum(len(c) for n, c in counts.items())
    print(f'Read {total} ngram counts from {fn}', file=sys.stderr)
    return counts


def conditional_probabilities(ngram_counts):
    grouped = defaultdict(lambda: defaultdict(list))
    for n in ngram_counts:
        for ngram, count in ngram_counts[n].items():
            mangled = NON_ASCII_ALPHA_RE.sub('�', ngram[-1])
            if mangled == ngram[-1]:
                continue    # only count strings with non-ascii alpha
            mangled_ngram = ngram[:-1] + (mangled,)
            grouped[n][mangled_ngram].append((ngram[-1], count))

    cond_prob = defaultdict(lambda: defaultdict(list))
    total_count = defaultdict(lambda: defaultdict(Counter))
    for n in ngram_counts:
        for ngram, word_counts in grouped[n].items():
            total = sum(c for w, c in word_counts)
            for word, count in word_counts:
                cond_prob[n][ngram].append((word, count/total))
            total_count[n][ngram] = total
    return cond_prob, total_count


def main(argv):
    args = argparser().parse_args(argv[1:])
    
    ngram_counts = read_ngram_counts(args.ngram_counts, args)
    cond_prob, total_count = conditional_probabilities(ngram_counts)

    stats = Counter()
    for fn in args.file:
        process_file(fn, cond_prob, total_count, stats, args)

    total = stats['total']
    for k, v in stats.items():
        try:
            print(f'{v}\t{k}\t({v/total:.1%})', file=sys.stderr)
        except:
            pass


if __name__ == '__main__':
    sys.exit(main(sys.argv))
