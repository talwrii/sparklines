#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Text-based sparklines, e.g. on the command-line like this: ▃▁▄▁▄█▂▅.

Please read the file README.rst for more information.
"""

from __future__ import unicode_literals, print_function, division

import re
import sys
import warnings

from future.builtins import round # bankers' rounding for Python 2


# handle different file types in Python 2 and 3
try:
    import io
    file = io.IOBase
except ImportError:
    pass

try:
    import termcolor
    HAVE_TERMCOLOR = True
except ImportError:
    HAVE_TERMCOLOR = False


__version__ = '0.4.1'

blocks = " ▁▂▃▄▅▆▇█"


def _rescale(x1, y1, x2, y2, x):
    "Evaluate a straight line through two points (x1, y1) and (x2, y2) at x."

    return (y2-y1) / (x2-x1) * x + (x2*y1 - x1-y2) / (x2-x1)


def _check_negatives(numbers):
    "Raise warning for negative numbers."

    negatives = filter(lambda x: x < 0, filter(None, numbers))
    if any(negatives):
        neg_values = ', '.join(map(str, negatives))
        msg = 'Found negative value(s): %s. ' % neg_values
        msg += 'While not forbidden, the output will look unexpected.'
        warnings.warn(msg)


def _get_color(emph, n):
    "Return true if this number should be emphasized"
    if emph is None:
        return None

    pat = '(\w+)\:(eq|gt|ge|lt|le)\:(.+)'
    for em in emph:
        color, op, value = re.match(pat, em).groups()
        value = float(value)
        if op == 'eq' and n == value:
            return color
        elif op == 'gt' and n > value:
            return color
        elif op == 'ge' and n >= value:
            return color
        elif op == 'lt' and n < value:
            return color
        elif op == 'le' and n <= value:
            return color
    return 'white'


def scale_values(numbers, num_lines=1, minimum=None, maximum=None):
    "Scale input numbers to appropriate range."

    # find min/max values, ignoring Nones
    filtered = [n for n in numbers if n is not None]
    min_ = min(filtered) if minimum is None else minimum
    max_ = max(filtered) if maximum is None else maximum
    dv = max_ - min_

    # clamp
    numbers = [max(min(n, max_), min_) for n in numbers]

    if dv == 0:
        values = [4 * num_lines for x in numbers]
    elif dv > 0:
        num_blocks = len(blocks) - 1

        values = [
            (num_blocks - 1.) / dv * x + (max_*1. - min_ * num_blocks) / dv
                if not x is None else None
            for x in numbers
        ]

        if num_lines > 1:
            m = min([n for n in values if n is not None])
            values = [
                _rescale(m, m, max_, num_lines * max_, v)
                    if not v is None else None
                for v in values
            ]
        values = [round(v) or 1 if not v is None else None for v in values]
    return values


def sparklines(numbers=[], num_lines=1, emph=None, verbose=False,
        minimum=None, maximum=None, wrap=None):
    """
    Return a list of 'sparkline' strings for a given list of input numbers.

    The list of input numbers may contain None values, too, for which the
    resulting sparkline will contain a blank character (a space).

    Examples:

        sparklines([3, 1, 4, 1, 5, 9, 2, 6])
        -> ['▃▁▄▁▄█▂▅']
        sparklines([3, 1, 4, 1, 5, 9, 2, 6], num_lines=2)
        -> [
            '     █ ▂',
            '▅▁▆▁██▃█'
        ]
    """

    assert num_lines > 0

    if len(numbers) == 0:
        return ['']

    # raise warning for negative numbers
    _check_negatives(numbers)

    display_values = scale_values(numbers, num_lines=num_lines, minimum=minimum, maximum=maximum)
    subgraphs_lines = []
    for subgraph_pairs in batch(wrap, zip(numbers, display_values)):
        columns = []
        for number, value in subgraph_pairs:
            column = _render_column(value, num_lines)
            color = _get_color(emph, number) if (HAVE_TERMCOLOR and emph) else None
            column = [_color_string(color, pixel) for pixel in column]
            columns.append(column)

        subgraph_rows = transpose_array(columns)
        subgraph_lines = list(map(''.join, subgraph_rows))
        subgraphs_lines.append(subgraph_lines)

    lines = list_join('', subgraphs_lines)
    return lines


def _render_column(value, num_lines):
    pixels = []
    for i in range(num_lines):
        block_code = min(max(0, value - 8*i), 8)
        pixels.append(blocks[block_code])
    return pixels


def _color_string(color, string):
    if not color:
        return string
    else:
        return ''.join(termcolor.colored(c, color) for c in string)


def list_join(separator, lists):
    result = []
    for lst, _next in zip(lists[:], lists[1:]):
        result.extend(lst)
        result.append(separator)

    if lists:
        result.extend(lists[-1])
    return result


def batch(batch_size, items):
    "Batch items into groups of batch_size"
    items = list(items)
    if batch_size is None:
        return [items]
    MISSING = object()
    padded_items = items + [MISSING] * (batch_size - 1)
    groups = zip(*[padded_items[i::batch_size] for i in range(batch_size)])
    return [[item for item in group if item != MISSING] for group in groups]


def transpose_array(array):
    line_lengths = set(map(len, array))
    if len(line_lengths) != 1:
        raise Exception('Inconsistent line lengths {!r}'.format(line_lengths))
    return list(reversed(list(map(list, zip(*array)))))


def demo(nums=[]):
    "Print a few usage examples on stdout."

    nums = nums or [3, 1, 4, 1, 5, 9, 2, 6]
    fmt = lambda num: '%g' % num if type(num) is float else 'None'
    nums1 = map(fmt, nums)

    if __name__ == '__main__':
        prog = sys.argv[0]
    else:
        prog = 'sparklines'


    print('Usage examples (command-line and programmatic use):')
    print('')

    print('- Standard one-line sparkline')
    print('%s %s' % (prog, ' '.join(nums1)))
    print('>>> print(sparklines([%s])[0])' % ', '.join(nums1))
    print(sparklines(nums)[0])
    print('')

    print('- Multi-line sparkline (n=2)')
    print('%s -n 2 %s' % (prog, ' '.join(nums1)))
    print('>>> for line in sparklines([%s], num_lines=2): print(line)' % ', '.join(nums1))
    for line in sparklines(nums, num_lines=2):
        print(line)
    print('')

    print('- Multi-line sparkline (n=3)')
    print('%s -n 3 %s' % (prog, ' '.join(nums1)))
    print('>>> for line in sparklines([%s], num_lines=3): print(line)' % ', '.join(nums1))
    for line in sparklines(nums, num_lines=3):
        print(line)
    print('')

    nums = nums + [None] + list(reversed(nums[:]))
    print('- Standard one-line sparkline with gap')
    print('%s %s' % (prog, ' '.join(nums1)))
    print('>>> print(sparklines([%s])[0])' % ', '.join(nums1))
    print(sparklines(nums)[0])
