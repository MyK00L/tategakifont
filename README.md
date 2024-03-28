# tategakifont

縦書きの対応がないシステムで縦書きがほしい時にフォントを９０度回して画面も９０度回したら縦書きだ。

このスクリプトはフォントを正確に９０度で回してくれる。

If you need vertical text in a syntem that does not support it, you can rotate by 90 degrees the font and the screen instead.

You can use this script to rotate the font by 90 degrees correctly.

## rules for rotation

The rules for rotating the glyphs can be found [here](https://www.unicode.org/reports/tr50/)

## Usage

You need python and fontforge installed.
You might also need to install some of the dependencies listed as imports at the top of `main.py` using `pip` or some other package manager.
To use the script, in the command line write: `python main.py input output`, where "input" is the input file name and "output" the output file name.

