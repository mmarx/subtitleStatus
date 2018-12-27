#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import re
from sbv_from_srt import sbv_from_srt


def chunks(file):
    """Read `file`, splitting it at doubled linebreaks"""
    lines = []
    for line in file:
        lines.append(re.sub(' {2,}', ' ', line.strip()))

    return '\n'.join(lines).split('\n\n')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit("usage: ./{} transcript.srt".format(sys.argv[0]))

    transcript = []
    try:
        with open(sys.argv[1], 'r') as file:
            raw = file.read().split('\n')
            transcript = chunks(sbv_from_srt(raw).split('\n'))
    except IOError as err:
        sys.exit("Transcript not readable: {}").format(err)

    out = ""

    for chunk in transcript:
        lines = chunk.split('\n')

        for line in lines[1:]:
            if line == '':
                continue
            out += ' ' + line

    print(out.replace('\n\n', '\n'))
