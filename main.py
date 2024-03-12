import urllib.request
import fontforge
import argparse
import psMat
import math
import re
import sys

# utility to print to stderr
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# Returns the table for font rotation
# Meaning of the table values:
# U: characters which are displayed upright, with the same orientation as they appears in the code charts.
# R: characters which are displayed sideways, rotated 90 degrees clockwise compared to the code charts.
# T, Tu, Tr: characters which are not just upright or sideways, but require a different glyph than in the code charts when used in vertical texts. In addition, Tu indicates that as a fallback, the character can be displayed with the code chart glyph upright; similarly, Tr indicates a possible fallback using the code chart glyph rotated 90 degrees clockwise. 
# see https://www.unicode.org/reports/tr50/tr50-8.html
def get_table():
    def line_to_range_type(x):
        x = x.replace(";"," ").split()
        m = re.match("(.*)\.\.(.*)",x[0])
        if m:
            return [[int(m.group(1),16),int(m.group(2),16)],x[1]]
        else:
            return [[int(x[0],16),int(x[0],16)],x[1]]
    #csv = urllib.request.urlopen("https://www.unicode.org/Public/vertical/revision-17/VerticalOrientation-17.txt").read().decode("utf-8")
    with open("VerticalOrientation.txt") as csv_file: # get table stored locally
        csv=csv_file.read()
    csv = re.sub(r"(?m)^#.*\n?", "", csv)
    table = list(map(line_to_range_type,filter(lambda x: not re.match("^\s*$",x) , csv.splitlines())))
    return table

# Returns true if the font has a sub for vertical text associated in the font
def has_vert_sub(g):
    return any((vs in ' '.join(map(lambda x: x[0], g.getPosSub("*"))) for vs in ["vert", "vrt", "Vert"]) )

def main():
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input font file name")
    parser.add_argument("output", help="output font file name")
    args = parser.parse_args()
    
    # Open intput font
    font = fontforge.open(args.input)
    
    # Modify name
    font.fontname+="-Rotated"
    font.fullname+=" Rotated"
    
    # Apply substitution for vertical text present in the font
    subbed = []
    for g in list(filter(has_vert_sub, font.glyphs())):
        if g.unicode==-1:
            continue
        c=chr(g.unicode)
        pos_sub = list(filter(lambda s: any(vs in s for vs in ["vert", "vrt", "Vert"]), map(lambda x: x[0], g.getPosSub("*"))) )[0]
        pos_sub = g.getPosSub(pos_sub)[0]
        if pos_sub[1]=="Substitution":
            font.selection.none()
            font.selection.select(pos_sub[2])
            font.copy()
            font.selection.none()
            font.selection.select(g)
            font.paste()
            font.selection.none()
            subbed.append(g.unicode)
        elif pos_sub[1]=="Position":
            g.width += pos_sub[-2] # horizontal advance
            g.vwidth += pos_sub[-1] # vertical advance
            tr = psMat.translate(pos_sub[-4],pos_sub[-3]) # position
            g.transform(tr,("round"))
            subbed.append(g.unicode)
        else:
            eprint("maybe unhandled: unknown",pos_sub,c,g.glyphname)
    
    # Select the glyphs that need to be rotated
    table = get_table()
    ranges = map(lambda x: x[0], filter(lambda x: x[1]=="U" or x[1]=="Tu", table))
    for rang in ranges: # select according to the table
        font.selection.select(("ranges","more"),*rang)
    for guni in subbed: # also select all those that have been substituted
        font.selection.select(("more",),guni)

    # Rotate selected glyphs based on the square center
    cx = font.em/2
    cy = font.em/2
    trcen = psMat.translate(-cx,-cy)
    rotcen = psMat.compose(trcen, psMat.compose(psMat.rotate(math.radians(90)), psMat.inverse(trcen)))
    font.transform(rotcen,("round"))

    # Save the output font
    font.generate(args.output)

if __name__=="__main__":
    main()

