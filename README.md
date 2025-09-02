# tategakifont

縦書きの対応がないシステムで縦書きがほしい時にフォントを９０度回して画面も９０度回したら縦書きだ。

このスクリプトはフォントを正確に９０度で回してくれる。

If you need vertical text in a system that does not support it, you can rotate the font and the screen by 90 degrees instead.

You can use this script to rotate the font by 90 degrees correctly.

## Rules for rotation

The rules for rotating the glyphs can be found [on the Unicode website](https://www.unicode.org/reports/tr50/).

## Usage

You need Python and FontForge installed. It has been tested to work with Python 3.8.10 and FontForge 20230101.

You shouldn't need to install any further dependencies, unless you are compiling FontForge from source.

To use the script, at the command line write: `python main.py input output`, where "input" is the input file name and "output" the output file name.

