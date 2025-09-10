import sys
import argparse
import math
import fontforge
import psMat

# Utility to print to stderr
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
        x = x.split()
        return [[int(x[0],16),int(x[1],16)],x[2]]
    with open("table.txt") as file: # get table stored locally
        contents=file.read()
    table = list(map(line_to_range_type,contents.splitlines()))
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

def apply_sub(font, tag, should_sub, subbed):
    if tag not in tagmap:
        eprint("No", tag, "in font")
        return
    for g in font.glyphs():
        pss = [item for tup in map(lambda st: g.getPosSub(st), tagmap[tag]) for item in tup]
        if len(pss)==0 or not should_sub(g):
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

# Get the value in the vert table for a unicode point
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

    # Open input font
    font = fontforge.open(args.input, ("allglyphsinttc","alltables"))
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
    apply_sub(font, "vert", lambda g: not (args.only_sub_table and table_at(table, g.unicode) not in ["T", "Tu", "Tr"]), subbed)
    # apply_sub(font,"vpal")
    # apply_sub(font,"vrt2",subbed) # what is this even ??
    # apply_sub(font,"vkna",subbed) # does this do something useful?

    # Select the glyphs that need to be rotated
    for g in font.glyphs():
        if table_at(table, g.unicode) in ["U","Tu"]:
            font.selection.select(("more",),g)

    # Select substitutions based on original glyph
    for g in font.glyphs():
        if g.unicode != -1:
            subs = g.getPosSub("*")
            for sub in subs:
                if sub[1] in ["Substitution","MultiSubs","AltSubs"]:
                    for j in range(2,len(sub)):
                        if font[sub[j]].unicode==-1:
                            if table_at(table, g.unicode) in ["U", "Tu"]:
                                font.selection.select(("more",),sub[j])
                            else:
                                font.selection.select(("less",),sub[j])

    # Select all glyphs that have been substituted with vert
    for g in subbed:
        font.selection.select(("more","singletons"),g)

    # Remove dist, kern, palt from rotated glyphs, move vkern and vpal to kern and palt
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
                            if row[2] != -1 and font.selection[font[row[2]]]:
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
    font.transform(rotcen, ("guide", "simplePos", "kernClasses"))
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

