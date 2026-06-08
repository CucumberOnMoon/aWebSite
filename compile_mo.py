"""Pure Python .po to .mo compiler for platforms without gettext."""
import struct
import sys


def unescape_po(s):
    """Convert PO escape sequences to actual characters."""
    result = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            c = s[i + 1]
            if c == 'n':
                result.append('\n')
            elif c == 't':
                result.append('\t')
            elif c == 'r':
                result.append('\r')
            elif c == '"':
                result.append('"')
            elif c == '\\':
                result.append('\\')
            else:
                result.append(s[i:i+2])
            i += 2
        else:
            result.append(s[i])
            i += 1
    return ''.join(result)


def compile_po_to_mo(po_path, mo_path):
    with open(po_path, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    entries = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip('\n').rstrip('\r')

        if line.startswith('msgid '):
            msgid_parts = []
            rest = line[6:].strip()
            if len(rest) >= 2 and rest[0] == '"' and rest[-1] == '"':
                msgid_parts.append(rest[1:-1])
            else:
                msgid_parts.append(rest)

            i += 1
            while i < len(lines):
                nxt = lines[i].rstrip('\n').rstrip('\r')
                if nxt.startswith('"') and not nxt.startswith('msgstr'):
                    t = nxt.strip()
                    if len(t) >= 2 and t[0] == '"' and t[-1] == '"':
                        msgid_parts.append(t[1:-1])
                    i += 1
                else:
                    break

            msgstr_parts = []
            if i < len(lines) and lines[i].startswith('msgstr '):
                rest = lines[i][7:].strip()
                if len(rest) >= 2 and rest[0] == '"' and rest[-1] == '"':
                    msgstr_parts.append(rest[1:-1])
                else:
                    msgstr_parts.append(rest)
                i += 1
                while i < len(lines):
                    nxt = lines[i].rstrip('\n').rstrip('\r')
                    if nxt.startswith('"') and not nxt.startswith('msgid') and not nxt.startswith('#'):
                        t = nxt.strip()
                        if len(t) >= 2 and t[0] == '"' and t[-1] == '"':
                            msgstr_parts.append(t[1:-1])
                        i += 1
                    else:
                        break

            msgid = unescape_po(''.join(msgid_parts))
            msgstr = unescape_po(''.join(msgstr_parts))
            entries.append((msgid, msgstr))
        else:
            i += 1

    entries.sort(key=lambda x: x[0])
    N = len(entries)

    HEADER = 28
    ORIG_TABLE = HEADER
    TRANS_TABLE = HEADER + N * 8

    string_data = b''
    orig_entries_bin = []
    trans_entries_bin = []

    string_offset = HEADER + N * 16

    for msgid, msgstr in entries:
        mid = msgid.encode('utf-8')
        mstr = msgstr.encode('utf-8')

        off = string_offset + len(string_data)
        string_data += mid + b'\x00'
        orig_entries_bin.append(struct.pack('<II', len(mid), off))

        off = string_offset + len(string_data)
        string_data += mstr + b'\x00'
        trans_entries_bin.append(struct.pack('<II', len(mstr), off))

    with open(mo_path, 'wb') as f:
        f.write(struct.pack('<IIIIIII', 0x950412de, 0, N, ORIG_TABLE, TRANS_TABLE, 0, 0))
        for e in orig_entries_bin:
            f.write(e)
        for e in trans_entries_bin:
            f.write(e)
        f.write(string_data)

    print(f'Compiled {N} translations to {mo_path}')
    return True


if __name__ == '__main__':
    po = sys.argv[1] if len(sys.argv) > 1 else r'd:\gitSpace\aWebSite\locale\zh_Hans\LC_MESSAGES\django.po'
    mo = sys.argv[2] if len(sys.argv) > 2 else r'd:\gitSpace\aWebSite\locale\zh_Hans\LC_MESSAGES\django.mo'
    compile_po_to_mo(po, mo)
