from functools import wraps
import re

class Error(Exception):
    pass

def replace_token_is(
    line,
    _re=re.compile(
        r'^((?:\\\r?\n)*[^\W0-9]\w*)((?:\s|\\\r?\n)+)is((?:\s|\\\r?\n)+)'
        r'([^\W0-9]\w*)(\s*)$'
    ),
):
    m = _re.match(line)
    if m:
        return f'{m.group(1)}:__yp__.theory{m.group(2)}=' \
               f'{m.group(3)}__yp__.category({m.group(4)}){m.group(5)}'
    else:
        return line

def outside_quotes(func):
    @wraps(func)
    def inner(line, *args, **kwargs):
        res = []
        for p, q in quote_split(line):
            res.append(func(p, *args, **kwargs))
            if q is not None:
                res.append(q)
        return ''.join(res)
    return inner

@outside_quotes
def replace_token_backtick(
    line,
    _re=re.compile(r'`([^\W0-9]\w*)`'),
):
    return _re.sub(r"__yp__.ref('\1')", line)

@open_parenthesis
def handle_class(
    line,
    _re=re.compile(
        r'^((?:\s|\\\r?\n)*class(?:\s|\\\r?\n)+[^\W0-9]\w*)'
        r'(>!|<!|!)?((?:\s|\\\r?\n)*)'
    ),
    _base={
        None: '__yp__.base',
        '>!': '__yp__.base_exists',
        '<!': '__yp__.base_unique',
        '!': '__yp__.base_exists_unique',
    },
):
    # This has to be applied before replace_exists, replace_unique.
    m = _re.search(line)
    if m:
        aline = line[m.span()[1]:]
        if aline[0] == '(':
            # The missing parenthesis occurs right after the parenthesis
            # that closes the parenthesis appearing as the first char of aline.
            rline = f'{m.group(1)}{m.group(3)}({_base[m.group(2)]}{aline}'
            return rline, len(rline) - len(aline) + 1, 1
        else:
            return f'{m.group(1)}{m.group(3)}({_base[m.group(2)]}()){aline}', 0, 0
    else:
        return line, 0, None

def put_lang_import(
    line,
    _re=re.compile(r'^((?:[^\S\r\n]|\\\r?\n)*)'),
):
    return _re.sub(r"\1import yampy.lang as __yp__;", line)

def close_parenthesis(line, offset, pcount):
    if pcount <= 0:
        return line, pcount
    
    for start, q_start, q_end in quote_ranges(line):
        s = max(start, offset)
        po = pc = None
        while True:
            if po is None or (po < s and po >= 0):
                po = line.find('(', s, q_start)
            if pc is None or (pc < s and pc >= 0):
                pc = line.find(')', s, q_start)
            if po >= 0 and (pc > po or pc < 0):
                pcount += 1
                s = po + 1
            elif pc >= 0 and (po > pc or po < 0):
                pcount -= 1
                s = pc + 1
                if pcount <= 0:
                    return f'{line[:s]}){line[s:]}', pcount
            else:
                break
                
    return line, pcount

@outside_quotes
def replace_exists(
    line,
    _re=re.compile(r'([^\W0-9]\w*)>!'),
):
    return _re.sub(r"__yp__.exists('\1')", line)

@outside_quotes
def replace_unique(
    line,
    _re=re.compile(r'([^\W0-9]\w*)<!'),
):
    return _re.sub(r"__yp__.unique('\1')", line)

@outside_quotes
def replace_proj_token(
    line,
    _re=re.compile(r'\$(\w*)'),
):
    return _re.sub(r"__yp__.proj('\1')", line)

def disallow_triple_quote(line):
    for start, q_start, q_end in quote_ranges(line):
        if start >= 2 and start == q_start:
            q3 = line[start-2:start+1]
            if q3 == '"""' or q3 == "'''":
                raise Error('Triple quote is not supported.') # TODO: Add line and filename in upper layer.
    return line

def disallow_fquote(line):
    for start, q_start, q_end in quote_ranges(line):
        if (
            q_start is not None and
            line[q_start-1:q_start+1] in ('f"', "f'")
        ):
            raise Error('f-strings are not supported.')
    return line

def disallow_semicolon(line):
    for start, q_start, q_end in quote_ranges(line):
        if line.find(';', start, q_start) >= 0:
            raise Error('semicolons are not supported.')
    return line

def disallow_defclass(
    line,
    _re=re.compile(r'^(?:\s|\\\r?\n)*(?:class|def)'),
):
    if _re.search(line):
        raise Error('class and def are not allowed here.')
    return line

def disallow_attrassign(
    line,
    _re=re.compile(r'^(?:\s|\\\r?\n)*[^\W0-9]\w*(?:\s|\\\r?\n)*[\.\[][^=]*=[^=]'),
):
    if _re.search(line):
        raise Error('Attribute and item assignment are not supported.')
    return line

def disallow_yp_keyword(
    line,
    _re=re.compile(r'(?:^|\W)__yp__(?:$|\W)'),
):
    for start, q_start, q_end in quote_ranges(line):
        if q_start is None:
            m = _re.search(line, start)
        else:
            m = _re.search(line, start, q_start)
        if m:
            raise Error('__yp__ is reserved')
    return line

def find_quote_start(line, offset, _idx_h=None):
    idx_d = line.find('"', offset)
    idx_s = line.find("'", offset)
    idx_h = _idx_h or line.find('#', offset)
    
    if (
        idx_d >= 0 and
        (idx_s > idx_d or idx_s < 0) and
        (idx_h > idx_d or idx_h < 0)
    ):
        return idx_d, '"'

    if (
        idx_s >= 0 and
        (idx_d > idx_s or idx_d < 0) and
        (idx_h > idx_s or idx_h < 0)
    ):
        return idx_s, "'"

    if (
        idx_h >= 0 and
        (idx_d > idx_h or idx_d < 0) and
        (idx_s > idx_h or idx_s < 0)        
    ):
        return idx_h, '#'

    return -1, None

def find_quote_end(
    line,
    offset,
    char,
    _re_s=re.compile(r"(?<=[^\\])(?:\\\\)*'"),
    _re_d=re.compile(r'(?<=[^\\])(?:\\\\)*"'),
):
    if char == '#':
        idx = line.find('\n', offset)
        if idx >= 0:
            return idx
    else:
        if char == "'":
            rgx = _re_s
        elif char == '"':
            rgx = _re_d
        m = rgx.search(line, offset)
        if m:
            return m.span()[1] - 1
    return len(line) - 1
    
def quote_ranges(line, handle_comment=False):
    start = 0
    while True:
        if handle_comment:
            idx, char = find_quote_start(line, start)
        else:
            idx, char = find_quote_start(line, start, _idx_h=-1)
        if idx >= 0:
            end = find_quote_end(line, idx+1, char)
            yield start, idx, end
            start = end + 1
        else:
            if start < len(line):
                yield start, None, None
            break
    return start

def quote_split(line):
    for start, q_start, q_end in quote_ranges(line):
        if q_start is None:
            q = None
        else:
            q = line[q_start:q_end+1]
        yield line[start:q_start], q

def comment_split(line):
    lstart = -1
    for start, q_start, q_end in quote_ranges(line, handle_comment=True):
        if lstart < 0:
            lstart = start
        if q_start is None:
            q = None
        elif line[q_start] != '#':
            continue
        else:
            q = line[q_start:q_end+1]
        yield line[lstart:q_start], q
        lstart = -1

def line_to_python(line, state):
    line = disallow_yp_keyword(line)
    line = disallow_triple_quote(line)
    line = disallow_fquote(line)
    line = disallow_semicolon(line)
    line = replace_token_is(line)
    line = replace_token_backtick(line)
    line, offset, pcount0 = handle_class(line)
    if pcount0 is not None:
        pcount = pcount0
    line, pcount = close_parenthesis(line, offset, pcount)
    line = replace_exists(line)
    line = replace_unique(line)
    line = replace_proj_token(line)
    state.pcount = pcount
    return line

class State:
    def __init__(self):
        self.pcount = 0
        self.lnum = 0
        self.filename = None

def first_module_line_to_python(line, state):
    line = line_to_python(line, state)
    if state.lnum == 0:
        try:
            line = disallow_defclass(line)
        except Error as e:
            raise Error(f'(In first line.) {e.args[0]}')
        line = put_lang_import(line)
    return line

def to_python(dst, src, state=None, is_module=False):
    def handle_part(part, filt, state):
        parts.append(part)
        if part.endswith('\\\n') or part.endswith('\\\r\n'):
            return False
        for line, comment in comment_split(''.join(parts)):
            dst.write(filt(line, state))
            if comment:
                dst.write(comment)
            state.lnum += line.count('\\\n') + line.count('\\\r\n')
        del parts[:]
        state.lnum += 1
        return True
    
    parts = []
    state = state or State()
    if is_module:
        filt0 = first_module_line_to_python
    else:
        filt0 = line_to_python
    try:
        for part in src:
            if handle_part(part, filt0, state):
                break
        for part in src:
            handle_part(part, line_to_python, state)
    except Error as e:
        raise Error(f'File {state.filename}, line {state.lnum}: {e.args[0]}')

def file_to_python(filename):
    import os
    # Allow up to two extensions, e.g. .y.py
    targetname, x = os.path.splitext(filename)
    targetname, x = os.path.splitext(targetname)
    targetname += '.py'
    state = State()
    state.filename = filename
    with open(filename) as fp:
        with open(targetname, 'w') as tp:
            to_python(tp, fp, state, is_module=True)

def main(argv):
    _, filename = argv
    file_to_python(filename)

if __name__ == '__main__':
    import sys
    main(sys.argv)