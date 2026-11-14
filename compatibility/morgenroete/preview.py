"""Render the patch's original typographic Workshop cover."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

out = Path(__file__).resolve().parent / 'preview.png'
image = Image.new('RGB', (800, 800), '#17242f')
draw = ImageDraw.Draw(image)
gold, cream = '#d4b980', '#f2ead7'
draw.rectangle((25,25,775,775),outline=gold,width=3)
draw.rectangle((36,36,764,764),outline='#74664b',width=1)
def line(text, y, size, color=cream, bold=False):
    font=ImageFont.truetype('C:/Windows/Fonts/georgiab.ttf' if bold else 'C:/Windows/Fonts/georgia.ttf',size)
    draw.text((400,y),text,font=font,fill=color,anchor='mm')
line('SPECULATIVE',130,45)
line('MARKETS',185,45)
draw.line((150,230,650,230),fill=gold,width=2)
line('FINANCE',320,32)
line('+',380,40,gold)
line('MORGENRÖTE',460,65,bold=True)
line('COMPATIBILITY',555,36,gold)
draw.line((150,620,650,620),fill=gold,width=2)
line('Load after both mods',680,25)
line('Separate patch for Victoria 3',725,20,'#bcc4c7')
image.save(out)
print(out)
