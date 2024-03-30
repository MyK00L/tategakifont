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
# T, Tu, Tr: characters which are not just upright or sideways, but require a different glyph than in the code charts when used in tertical texts. In addition, Tu indicates that as a fallback, the character can be displayed with the code chart glyph upright; similarly, Tr indicates a possible fallback using the code chart glyph rotated 90 degrees clockwise.
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
    return any((vs in ' '.join(map(lambda x: x[0], g.getPosSub("*"))) for vs in ["vert", "vrt", "vkna", "Vert"]) )

tagmap = {}
ttlook = {}
def fill_tagmap(font):
    lookups = font.gpos_lookups + font.gsub_lookups
    for lookup in lookups:
        tags = map(lambda x: x[0], font.getLookupInfo(lookup)[2])
        tables = font.getLookupSubtables(lookup)
        for tag in tags:
            if tag not in ttlook:
                ttlook[tag] = []
            ttlook[tag].append(lookup)
            if tag not in tagmap:
                tagmap[tag] = []
            for table in tables:
                tagmap[tag].append(table)

def apply_sub(font, tag, subbed=[]):
    if tag not in tagmap:
        eprint("No", tag, "in font")
        return
    for g in font.glyphs():
        pss = [item for tup in map(lambda st: g.getPosSub(st), tagmap[tag]) for item in tup]
        if len(pss)==0:
            continue
        ps = pss[0]
        if ps[1] in ["Substitution","AltSubs"]:
            font.selection.none()
            font.selection.select(ps[2])
            font.copy()
            font.selection.none()
            font.selection.select(g)
            font.paste()
            font.selection.none()
            subbed.append(g)
        elif ps[1]=="Position":
            g.width += ps[-2] # horizontal advance
            g.vwidth += ps[-1] # vertical advance
            tr = psMat.translate(ps[-4],ps[-3]) # position
            g.transform(tr)
            subbed.append(g)
        else:
            eprint("Unhandled",ps[1],tag,"for glyph",g)

def table_at(table, code):
    lb = -1
    ub = len(table)
    while lb<ub-1:
        m = (lb+ub)//2
        if table[m][0][0] <= code:
            lb = m
        else:
            ub = m
    if table[lb][0][0] <= code and code <= table[lb][0][1]:
        return table[lb][1]
    return "None"

def main():
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input font file name")
    parser.add_argument("output", help="output font file name")
    parser.add_argument("--half-to-full", action="store_true", help="replace halfwidth glyphs with fullwidth, this will make all english letters and punctuation upright")
    parser.add_argument("--only-sub-table", action="store_true", help="apply glyph substitutions only if they are marked as T, Tu or Tr in the vertical orientation property table")
    parser.add_argument("--no-round", action="store_true", help="do not round all glyph points in the output font")
    parser.add_argument("--rotation-center", choices=["halfemdesc","halfem","bb"],default="halfemdesc",help="middle point for rotation:\nbb = bounding box of all glyphs to be rotated,\nhalfem = (em/2,em/2),\nhalfemdesc = (em/2,em/2-descent)")
    args = parser.parse_args()

    table = get_table()

    # Open intput font
    font = fontforge.open(args.input)
    if font.is_cid:
        font.cidFlatten()

    # Modify name
    if font.fontname is not None:
        font.fontname+="-Rotated"
    if font.fullname is not None:
        font.fullname+=" Rotated"

    fill_tagmap(font)

    # Apply substitution for vertical text present in the font
    subbed=[]
    apply_sub(font,"vert",subbed)
    # apply_sub(font,"vpal")
    # apply_sub(font,"vrt2",subbed) # what is this even ??
    # apply_sub(font,"vkna",subbed) # does this do something useful?

    # Select the glyphs that need to be rotated
    '''
    ranges = map(lambda x: x[0], filter(lambda x: x[1]=="U" or x[1]=="Tu", table))
    for rang in ranges: # select according to the table
        font.selection.select(("unicode","more","ranges"),*rang)
    '''
    for g in font.glyphs():
        if table_at(table, g.unicode) in ["U","Tu"]:
            font.selection.select(("more",),g)

    for g in font.selection.byGlyphs:
        subs = g.getPosSub("*")
        for sub in subs:
            if sub[1] in ["Substitution","MultiSubs","AltSubs"]:
                for j in range(2,len(sub)):
                    if font[sub[j]].unicode==-1:
                        font.selection.select(("more",),sub[j])

    for g in subbed: # also select all those that have been substituted
        font.selection.select(("more","singletons"),g)

    # remove dist, kern, palt from rotated glyphs, move vkern and vpal to kern and palt
    for g in font.glyphs():
        if font.selection[g]:
            for tag in ["palt","kern","dist"]:
                if tag in tagmap:
                    for st in tagmap[tag]:
                        g.removePosSub(st)
        else:
            for tag in ["kern","dist"]:
                if tag in tagmap:
                    for st in tagmap[tag]:
                        delete = False
                        for row in g.getPosSub(st):
                            if font.selection[font[row[2]]]:
                                #TODO: delete only this row
                                delete = True
                                break
                        if delete:
                            g.removePosSub(st)

    # Rotate selected glyphs
    cx = font.em/2
    cy = font.em/2-font.descent
    if args.rotation_center == "bb":
        bbb = [font.em*8,font.em*8,-font.em*8,-font.em*8]
        for g in font.selection.byGlyphs:
            bb = g.boundingBox()
            bbb[0] = min(bbb[0],bb[0])
            bbb[1] = min(bbb[1],bb[1])
            bbb[2] = max(bbb[2],bb[2])
            bbb[3] = max(bbb[3],bb[3])
        cx = (bb[2]+bb[0])/2
        cy = (bb[3]+bb[1])/2
    elif args.rotation_center == "halfem":
        cx = font.em/2
        cy = font.em/2
    trcen = psMat.translate(-cx,-cy)
    rotcen = psMat.compose(trcen, psMat.compose(psMat.rotate(math.radians(90)), psMat.inverse(trcen)))
    font.transform(rotcen)
    font.selection.none()

    if args.half_to_full:
        for chw in range(33,127):
            cfw = chw+0xfee0
            font.selection.select(("unicode","singletons"),cfw)
            font.copy()
            font.selection.none()
            font.selection.select(("unicode","singletons"),chw)
            font.paste()
            font.selection.none()

    if not args.no_round:
        font.selection.all()
        font.round()
        font.selection.none()

    # Save the output font
    font.generate(args.output)

if __name__=="__main__":
    main()

