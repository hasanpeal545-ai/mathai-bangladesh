"""Claude (chat) manual corrections of recurring-decimal dots, checked against page images.
Notation in this file: a ' after a digit = combining dot U+0307 over that digit.
Usage: python manual_dotfix.py <page_file> <fixes_json>; backs up original as .before_dotfix.txt"""
import sys, json, shutil, re
def d(s): return re.sub(r"(\d)'", lambda m: m.group(1)+"̇", s)
page, fixes = sys.argv[1], json.load(open(sys.argv[2], encoding="utf-8"))
t = open(page, encoding="utf-8").read()
shutil.copy(page, page.replace(".txt", ".before_dotfix.txt"))
for old, new in fixes:
    old2 = d(old)
    if old2 not in t: print("NOT FOUND:", old); continue
    t = t.replace(old2, d(new))
open(page, "w", encoding="utf-8").write(t)
print("ok", page)
