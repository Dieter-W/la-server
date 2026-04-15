# Employee numbers and check digits

This project stores each camp participant’s **employee number** (children and staff in the Spielstadt) as an alphanumeric string (see [`employees.employee_number` in the database design](./database_design.md#employees)). When `VALIDATE_CHECK_SUM` is enabled in `.env` (the default), the HTTP APIs and the [bulk import script](../README.md#csv-bulk-import) require that number to pass the **ISO 7064 Mod 97,10** check. That way a typo is unlikely to accidentally match another camp participant’s number.

For `VALIDATE_CHECK_SUM` and related environment variables, see [Optional environment variables in the README](../README.md#optional-environment-variables).

## What Mod 97,10 means here

The algorithm is the same family as the IBAN check: the full string (including two trailing check characters) must satisfy a modulo-97 rule. Internally, each character is converted to a decimal digit string (each symbol is interpreted in base 36, then those decimal chunks are concatenated), the payload is extended with `00`, and two check digits are chosen so that the complete number validates.

Details: ISO 7064 and the [`python-stdnum` package](https://pypi.org/project/python-stdnum/) (`stdnum.iso7064.mod_97_10`; [source](https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/iso7064/mod_97_10.py)).

## Python (`python-stdnum`)

The server uses this library—keep imports aligned with [app/routes/employees.py](../app/routes/employees.py).

Install (or use the project’s Poetry environment, which already lists `python-stdnum` in [`pyproject.toml`](../pyproject.toml)):

```bash
pip install "python-stdnum>=2.2,<3"
```

**Compute the two check characters** for a base payload (everything except the final two check digits), then build the full employee number:

```python
from stdnum.iso7064 import mod_97_10

# Base payload without check digits (examples used in API docs / tests)
base = "M001"
check_digits = mod_97_10.calc_check_digits(base)  # two characters, e.g. "55"
employee_number = base + check_digits  # e.g. "M00155"

assert mod_97_10.is_valid(employee_number)

# Another valid example
base2 = "A002"
full2 = base2 + mod_97_10.calc_check_digits(base2)  # "A00265"
assert mod_97_10.is_valid(full2)
```

`calc_check_digits` returns a string of length two (often digits). `is_valid` is what the API relies on when checksum validation is on.

## Excel

### Why normal worksheet formulas are fragile

After letters are expanded to decimal digits, the string can be **long**. Excel stores numbers with about **15 significant digits** of precision, so a single `MOD()` on a “number” built from the whole string is unreliable. Prefer either a **chunked numeric** approach for short purely numeric cases, or a **VBA user-defined function** that walks the string digit by digit (equivalent to big-integer modulo).

### Option A — Worksheet formula (numeric-only demo)

For a **pure numeric** string in `A1` that you can safely split into two parts (each part within Excel’s precision when combined), you can combine remainders—for example when the left part has 10 digits:

```excel
=MOD(MOD(LEFT(A1,10),97)*10^(LEN(A1)-10)+RIGHT(A1,LEN(A1)-10),97)
```

This is only a **demonstration** of splitting a large value for `MOD 97`; it does **not** implement the full ISO character expansion used by the server. For real employee numbers with letters, use Option B.

**Localized Excel:** In many European locales, formulas use `;` instead of `,` between arguments, and function names differ (e.g. German `REST`, `LINKS`, `RECHTS`, `LÄNGE` instead of `MOD`, `LEFT`, `RIGHT`, `LEN`).

### Option B — VBA UDF (recommended)

This mirrors `python-stdnum`’s `mod_97_10`: each character is converted with base 36 (`A`→10 … `Z`→35; digits stay as digits), the digit string is appended with `00`, and the two check characters are `98 - (value mod 97)` formatted as two digits.

1. Press **Alt+F11** → **Insert** → **Module**.
2. Paste:

```vb
' Returns the two Mod 97,10 check characters for ISO 7064 (same idea as python-stdnum.mod_97_10).
Function Iso7064Mod97CheckDigits(ByVal text As String) As String
    Dim i As Long
    Dim c As String
    Dim digits As String
    Dim rest As Long
    Dim temp As String

    text = UCase$(text)
    For i = 1 To Len(text)
        c = Mid$(text, i, 1)
        If c >= "A" And c <= "Z" Then
            digits = digits & CStr(Asc(c) - 55)   ' A=10 ... Z=35, same as Int(char, 36) for A-Z
        ElseIf c >= "0" And c <= "9" Then
            digits = digits & c
        End If
    Next i

    temp = digits & "00"
    rest = 0
    For i = 1 To Len(temp)
        rest = (rest * 10 + CLng(Mid$(temp, i, 1))) Mod 97
    Next i

    Iso7064Mod97CheckDigits = Format$(98 - rest, "00")
End Function
```

**Use in a sheet** (base in `A1`, no check digits yet):

```excel
=A1 & Iso7064Mod97CheckDigits(A1)
```

Examples that match Python: base `M001` → `M00155`; base `A002` → `A00265`.

## Operations and database

- Bulk import: [`scripts/bulk_import_employees.py`](../scripts/bulk_import_employees.py) and [README.md — CSV bulk import](../README.md#csv-bulk-import). Use `--nochecksum-check` only when you intentionally skip validation (not recommended for production).
- The database does **not** enforce the checksum; validation happens in the application when `VALIDATE_CHECK_SUM` is true ([`database_design.md`](./database_design.md#employees)).
