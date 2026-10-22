#!/usr/bin/env python3
"""Prepare a standalone STRIDE table for the Excalidraw web editor."""
import csv
import hashlib
import json
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
with (HERE / 'STRIDE.csv').open(encoding='utf-8-sig', newline='') as file:
    rows = list(csv.DictReader(file))
assert [int(row['ID']) for row in rows] == list(range(1, 10))

elements = []
group = 'notesapp-stride-table'


def add(kind, x, y, width, height, **extra):
    ident = f'stride-table-{len(elements):03d}'
    seed = int(hashlib.sha256(ident.encode()).hexdigest()[:7], 16)
    element = dict(id=ident, type=kind, x=x, y=y, width=width, height=height,
                   angle=0, strokeColor='#bdd5e6', backgroundColor='transparent',
                   fillStyle='solid', strokeWidth=1.5, strokeStyle='solid', roughness=0,
                   opacity=100, groupIds=[group], frameId=None, roundness=None,
                   seed=seed, version=1, versionNonce=seed, index=None, isDeleted=False,
                   boundElements=None, updated=1, link=None, locked=False)
    element.update(extra)
    elements.append(element)
    return element


def text(x, y, value, size=21, color='#102637', width=None, **extra):
    if width:
        value = '\n'.join(textwrap.fill(line, max(8, int(width / (size * .60))),
                                       break_long_words=False, break_on_hyphens=False)
                          for line in value.splitlines())
    lines = value.splitlines()
    return add('text', x, y, max(map(len, lines)) * size * .61, len(lines) * size * 1.25,
               strokeColor=color, fontSize=size, fontFamily=2, text=value, originalText=value,
               textAlign='left', verticalAlign='top', containerId=None,
               autoResize=True, lineHeight=1.25, **extra)


text(40, 28, 'STRIDE analysis · NotesApp', 42)
text(40, 94, 'Nine numbered flows · potential threats · no attack testing', 24, '#476a85')
text(40, 138, 'D: availability scenarios to assess. Flow 8 DB privilege scope still needs verification.',
     22, '#476a85')

col_widths = [70, 345, 280, 315, 300, 325, 280, 345]
headers = ['ID', 'Numbered flow', 'S\nSpoofing', 'T\nTampering', 'R\nRepudiation',
           'I\nInformation disclosure', 'D\nDenial of service', 'E\nElevation of privilege']
left, top, header_height, row_height = 40, 205, 82, 150
total_width = sum(col_widths)
total_height = header_height + len(rows) * row_height
add('rectangle', left, top, total_width, header_height, backgroundColor='#e4f1f8')
for i in range(len(rows)):
    add('rectangle', left, top + header_height + i * row_height, total_width, row_height,
        backgroundColor='#ffffff' if i % 2 == 0 else '#f5f9fc')

x = left
for width, heading in zip(col_widths, headers):
    text(x + 14, top + 14, heading, 22, '#00749b', width=width - 28)
    x += width
    if x < left + total_width:
        add('line', x, top, 0, total_height, points=[[0, 0], [0, total_height]],
            startBinding=None, endBinding=None, startArrowhead=None, endArrowhead=None)

for i, row in enumerate(rows):
    x = left
    for key, width in zip(['ID', 'Flow', 'S', 'T', 'R', 'I', 'D', 'E'], col_widths):
        value = row[key].replace(' -> ', ' → ')
        if key == 'Flow':
            value = value.replace(': ', '\n', 1)
        cell = text(x + 14, top + header_height + i * row_height + 18, value, 21,
                    '#9b650b' if key == 'ID' else '#102637', width=width - 28,
                    customData={'flowId': int(row['ID']), 'column': key})
        assert cell['height'] <= row_height - 30, (row['ID'], key, cell['text'])
        x += width

scene = dict(type='excalidraw', version=2, source='https://excalidraw.com', elements=elements,
             appState={'viewBackgroundColor': '#ffffff', 'gridSize': None, 'theme': 'light'}, files={})
output = HERE / 'NotesApp-STRIDE.excalidraw'
output.write_text(json.dumps(scene, ensure_ascii=False, indent=2) + '\n')
print(f'Prepared {len(rows)} table rows and {len(elements)} native elements')
