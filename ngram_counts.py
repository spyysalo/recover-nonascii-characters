#!/usr/bin/python3

import sys
import re
import gzip

from collections import Counter, defaultdict
from argparse import ArgumentParser


DESCRIPTION = 'Get counts for N-grams with non-ASCII alphabetic characters'


TOKENIZATION_RE = re.compile('([^\W\d_]+|\d+|\s+|.)')


NON_ASCII_ALPHA_RE = re.compile('[^\W\d_a-zA-Z]')


def argparser():
    ap = ArgumentParser(description=DESCRIPTION)
    ap.add_argument('-l', '--lowercase', default=False, action='store_true')
    ap.add_argument('-n', default=2, type=int)
    ap.add_argument('text', nargs='+')
    return ap


def tokenize(sentence):
    tokens = TOKENIZATION_RE.split(sentence)
    tokens = ['<s>'] + [t for t in tokens if t and not t.isspace()] + ['</s>']
    return tokens


def ngrams(tokens, n):
    return [tokens[i:i+n] for i in range(len(tokens)-n+1)]


def contains_non_ascii_alpha(string):
    return NON_ASCII_ALPHA_RE.search(string)


def count_ngrams(stream, counts, options):
    for ln, l in enumerate(stream, start=1):
        if options.lowercase:
            l = l.lower()
        for n in range(1, options.n+1):
            for ngram in ngrams(tokenize(l), n):
                if contains_non_ascii_alpha(ngram[-1]):
                    counts[n][' '.join(ngram)] += 1
    return counts


def main(argv):
    args = argparser().parse_args(argv[1:])

    gzopen = lambda fn: gzip.open(fn, 'rt', encoding='utf-8')

    counts = defaultdict(Counter)
    for fn in args.text:
        xopen = gzopen if fn.endswith('.gz') else open
        with xopen(fn) as f:
            count_ngrams(f, counts, args)

    print('\\data\\')
    for n in range(1, args.n+1):
        total = sum(counts[n].values())
        print(f'ngram {n}={total}')
    for n in range(1, args.n+1):
        print(f'\n\\{n}-grams:')
        for k, v in sorted(counts[n].items(), key=lambda d: -d[1]):
            print(f'{v}\t{k}')
    print('\n\\end\\')


if __name__ == '__main__':
    sys.exit(main(sys.argv))
