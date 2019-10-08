# Use regular expression replacements (stack program for reveal) to strip all zkay specific language features
# so that code can be passed to solc for type checking.

import re
from typing import Pattern

# Declaration for me which is injected into each contract
ME_DECL = ' address private me = msg.sender;'

# ---------  Lexer Rules ---------

WS_PATTERN = r'[ \t\r\n\u000C]'
ID_PATTERN = r'[a-zA-Z\$_][a-zA-Z0-9\$_]*'
BT_PATTERN = r'(?:address|bool|uint)'
NONID_START = r'(?:[^a-zA-Z0-9\$_]|^)'
NONID_END = r'(?:[^a-zA-Z0-9\$_]|$)'
PARENS_PATTERN = re.compile(r'[()]')
STRING_OR_COMMENT_PATTERN = re.compile(
    r'(?P<repl>'
    r'(?://[^\r\n]*)'                           # match line comment
    r'|(?:/\*.*?\*/)'                           # match block comment
    r"|(?:(?<=')(?:[^'\r\n\\]|(?:\\.))*(?='))"  # match single quoted string literal
    r'|(?:(?<=")(?:[^"\r\n\\]|(?:\\.))*(?="))'  # match double quoted string literal
    r')', re.DOTALL
)

# ---------  Parsing ---------

# Regex to match contract declaration
CONTRACT_DECL_PATTERN = re.compile(f'(?P<keep>{NONID_START}contract{WS_PATTERN}*{ID_PATTERN}{WS_PATTERN}*{"{"}[^\\n]*?)'
                                   f'(?<!{ME_DECL})(?P<repl>\\n)')

# Regex to match annotated types
ATYPE_PATTERN = re.compile(f'(?P<keep>{NONID_START}{BT_PATTERN}{WS_PATTERN}*)'  # match basic type
                           f'(?P<repl>@{WS_PATTERN}*{ID_PATTERN})')             # match @owner

# Regexes to match 'all' and 'final'
MATCH_WORD_FSTR = f'(?P<keep>{NONID_START})(?P<repl>{{}})(?={NONID_END})'
FINAL_PATTERN = re.compile(MATCH_WORD_FSTR.format('final'))
ALL_PATTERN = re.compile(MATCH_WORD_FSTR.format('all'))

# Regex to match tagged mapping declarations
MAP_PATTERN = re.compile(
    f'(?P<keep>{NONID_START}mapping{WS_PATTERN}*\\({WS_PATTERN}*address{WS_PATTERN}*)'  # match 'mapping (address'
    f'(?P<repl>!{WS_PATTERN}*{ID_PATTERN})'                                             # match '!tag'
    f'(?={WS_PATTERN}*=>{WS_PATTERN}*)')                                                # expect '=>'

# Regex to detect start of reveal
REVEAL_START_PATTERN = re.compile(f'(?:^|(?<=[^\\w]))reveal{WS_PATTERN}*(?=\\()')  # match 'reveal', expect '('


def create_surrogate_string(instr: str):
    """
    Preserve newlines and replace all other characters with spaces
    :return whitespace string with same length as instr and with the same line breaks
    """
    return ''.join(['\n' if e == '\n' else ' ' for e in instr])


# Replacing reveals only with regex is impossible because they could be nested -> do it with a stack
def strip_reveals(code: str):
    matches = re.finditer(REVEAL_START_PATTERN, code)
    for m in matches:
        before_reveal_loc = m.start()
        reveal_open_parens_loc = m.end()

        # Find matching closing parenthesis
        idx = reveal_open_parens_loc + 1
        open = 1
        while open > 0:
            cstr = code[idx:]
            idx += re.search(PARENS_PATTERN, cstr).start()
            open += 1 if code[idx] == '(' else -1
            idx += 1

        # Go backwards to find comma before owner tag
        last_comma_loc = code[:idx].rfind(',')
        reveal_close_parens_loc = idx - 1

        # Replace reveal by its inner expression + padding
        code = f'{code[:before_reveal_loc]}' \
               f'{create_surrogate_string(code[before_reveal_loc:reveal_open_parens_loc])}' \
               f'{code[reveal_open_parens_loc:last_comma_loc]}' \
               f'{create_surrogate_string(code[last_comma_loc:reveal_close_parens_loc])}' \
               f'{code[reveal_close_parens_loc:]}'
    return code


def replace_with_surrogate(code: str, search_pattern: Pattern, replacement_fstr: str = '{}'):
    """
    Replaces all occurrences of search_pattern in code with:
        content of capture group <keep> (if any) + either
        a) replacement_fstr (if replacement_fstr does not contain '{}')
        b) replacement_fstr with {} replaced by whitespace corresponding to content of capture group <repl>
            (such that replacement length == <repl> length with line breaks preserved)

    The <repl> capture group must be the last thing that is matched in search pattern
    """
    keep_repl_pattern = r'\g<keep>' if '(?P<keep>' in search_pattern.pattern else ''
    has_ph = '{}' in replacement_fstr
    replace_len = len(replacement_fstr) - 2
    replacement = replacement_fstr
    search_idx = 0
    while True:
        match = re.search(search_pattern, code[search_idx:])
        if match is None:
            return code
        if has_ph:
            replacement = replacement_fstr.format(create_surrogate_string(match.groupdict()["repl"])[replace_len:])

        code = code[:search_idx] + re.sub(search_pattern, keep_repl_pattern + replacement, code[search_idx:], count=1)
        search_idx += match.end() + 1


def fake_solidity_code(code: str):
    """
    Returns the solidity code to which the given zkay_code corresponds when dropping all privacy features,
    while preserving original formatting
    """

    # Strip string literals and comments
    code = replace_with_surrogate(code, STRING_OR_COMMENT_PATTERN)

    # Strip final
    code = replace_with_surrogate(code, FINAL_PATTERN)

    # Strip ownership annotations
    code = replace_with_surrogate(code, ATYPE_PATTERN)

    # Strip map key tags
    code = replace_with_surrogate(code, MAP_PATTERN)

    # Strip reveal expressions
    code = strip_reveals(code)
    assert re.search(ALL_PATTERN, code) is None

    # Inject me address declaration (should be okay for type checking, maybe not for program analysis)
    # An alternative would be to replace me by msg.sender, but this would affect code length (error locations)
    code = replace_with_surrogate(code, CONTRACT_DECL_PATTERN, ME_DECL + '\n')

    return code
