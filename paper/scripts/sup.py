import re
SUP=dict(zip("0123456789+-−=()abcdefghijklmnoprstuvwxyz","⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁻⁼⁽⁾ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ"))
def conv(s):
    s=s.replace(" ","")
    return "".join(SUP[c] for c in s) if all(c in SUP for c in s) else None
def fix(t):
    def r(m):
        c=conv(m.group(1)); return c if c else "^("+m.group(1)+")"
    t=re.sub(r"\^\{([^{}]+)\}",r,t)
    t=re.sub(r"\^([a-z0-9])",lambda m: SUP.get(m.group(1),"^"+m.group(1)),t)
    return t
