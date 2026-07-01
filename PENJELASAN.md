# Tugas UAS — Representasi Tahapan Kompilasi

**Konstruksi yang dipilih:** Perulangan (*Looping*) — `for`

---

## 1. Pilihan Konstruksi

Konstruksi yang diimplementasikan adalah **perulangan `for`**, dengan bentuk umum:

```
for (init; condition; update) {
    statements
}
```

Contoh konkret yang dipakai sebagai kasus uji:

```c
int i = 0;
int total = 0;
int y = 0;
for (i = 0; i < 5; i = i + 1) {
    total = total + i;
    y = i * 2;
}
```

---

## 2. Pattern / Pola Sintaksis (BNF)

```text
<program>    ::= { <statement> }

<statement>  ::= <var_decl>
              |  <assign_stmt>
              |  <for_stmt>

<var_decl>   ::= "int" <identifier> "=" <expr> ";"

<assign_stmt>::= <identifier> "=" <expr> ";"

<for_stmt>   ::= "for" "(" <init> ";" <condition> ";" <update> ")"
                 "{" { <statement> } "}"

<init>       ::= <identifier> "=" <expr>
<update>     ::= <identifier> "=" <expr>
<condition>  ::= <expr> <relop> <expr>

<expr>       ::= <term>  { ("+" | "-") <term>  }
<term>       ::= <factor> { ("*" | "/") <factor> }
<factor>     ::= <number> | <identifier> | "(" <expr> ")"

<relop>      ::= "==" | "!=" | "<" | "<=" | ">" | ">="
```

Pola ini didefinisikan agar mendukung ekspresi aritmatika bertingkat (perkalian/pembagian
lebih diprioritaskan daripada penjumlahan/pengurangan) di dalam `init`, `condition`,
`update`, maupun badan perulangan.

---

## 3. Implementasi Program

Program ditulis dalam **Python 3** (`compiler.py`) dan dibagi menjadi 4 komponen yang
saling berurutan, meniru pipeline compiler yang sesungguhnya.

### 3.1 Tahap Leksikal — `tokenize()`

- Menggunakan **regular expression** (modul `re`) untuk memecah source code menjadi
  token: `TYPE`, `FOR`, `ID`, `NUMBER`, `RELOP`, `ASSIGN`, `PLUS`, `MINUS`, `TIMES`,
  `DIVIDE`, `LPAREN`, `RPAREN`, `LBRACE`, `RBRACE`, `SEMI`.
- Karakter whitespace dan komentar (`//...`) diabaikan (`SKIP`, `COMMENT`).
- Jika ditemukan karakter yang tidak cocok dengan pola manapun, lexer akan melempar
  `LexicalError` beserta posisi karakternya.

Contoh keluaran token untuk `i = i + 1`:

```
ID       : i
ASSIGN   : =
ID       : i
PLUS     : +
NUMBER   : 1
```

### 3.2 Tahap Sintaksis — `Parser` (Recursive Descent)

- Parser membaca deretan token dan membangun **Abstract Syntax Tree (AST)** sesuai
  aturan BNF di atas, menggunakan teknik *recursive descent parsing*.
- Node AST yang dibentuk: `Program`, `VarDecl`, `Assign`, `ForLoop`, `BinOp`, `Var`,
  `Num`.
- Prioritas operator (`*`, `/` lebih tinggi dari `+`, `-`) ditangani melalui pemisahan
  fungsi `parse_expr()` dan `parse_term()`.
- Kesalahan struktur (misal `for` tanpa `else`... eh tanpa kurung tutup, token yang
  tidak sesuai urutan, dsb.) akan melempar `SyntaxErrorCustom`.

Potongan AST untuk `for (i = 0; i < 5; i = i + 1) { ... }`:

```
ForLoop
  init:      Assign(i, Num(0))
  condition: BinOp(<, Var(i), Num(5))
  update:    Assign(i, BinOp(+, Var(i), Num(1)))
  body:      [ Assign(total, ...), Assign(y, ...) ]
```

### 3.3 Tahap Semantik — `SemanticAnalyzer`

Pengecekan dasar yang dilakukan (menggunakan **symbol table** berbentuk dictionary):

1. **Deklarasi ganda** — variabel yang sama tidak boleh dideklarasikan dua kali.
2. **Variabel belum dideklarasikan** — setiap variabel yang dipakai (di kondisi,
   update, maupun badan loop) harus sudah ada di symbol table.
3. **Kecocokan tipe** — karena bahasa mini ini hanya memiliki tipe `int`, pengecekan
   tipe dilakukan secara rekursif pada setiap `BinOp` (kedua operand harus bertipe
   sama).

Jika salah satu aturan dilanggar, program melempar `SemanticError`. Hal ini
didemonstrasikan pada `compiler.py` bagian "DEMO PENANGANAN ERROR SEMANTIK", di mana
variabel `z` dipakai tanpa dideklarasikan lebih dulu sehingga menghasilkan:

```
[GAGAL KOMPILASI - SESUAI EKSPEKTASI] SemanticError: Variabel 'z' digunakan sebelum dideklarasikan.
```

### 3.4 Tahap Generasi Kode — `TACGenerator` (Three-Address Code)

Pola terjemahan **for-loop → TAC** yang digunakan mengikuti pola standar buku teks
kompilasi (mirip terjemahan `while`, ditambah blok inisialisasi & update):

```
<init>
L_start:
    t = <condition>
    ifFalse t goto L_end
    <isi badan loop, tiap ekspresi majemuk dipecah pakai variabel temporer t1, t2, ...>
    <update>
    goto L_start
L_end:
```

Setiap sub-ekspresi biner (`a + b`, `a * b`, dst.) dipecah menjadi instruksi TAC
tersendiri menggunakan variabel sementara (`t1`, `t2`, ...) — inilah inti dari
*Three-Address Code*: setiap instruksi maksimal memiliki satu operator dan tiga
alamat (hasil, operand1, operand2).

---

## 4. Hasil Uji Coba (Output Program)

Untuk source code:

```c
int i = 0;
int total = 0;
int y = 0;
for (i = 0; i < 5; i = i + 1) {
    total = total + i;
    y = i * 2;
}
```

Program menghasilkan **Three-Address Code**:

```
i = 0
total = 0
y = 0
i = 0
L1:
t1 = i < 5
ifFalse t1 goto L2
t2 = total + i
total = t2
t3 = i * 2
y = t3
t4 = i + 1
i = t4
goto L1
L2:
```

Keluaran lengkap (token, AST, symbol table, dan TAC untuk kedua kasus uji — termasuk
kasus error) dapat dilihat dengan menjalankan:

```bash
python3 compiler.py
```

---

## 5. Struktur Repositori

```
.
├── compiler.py       # Implementasi lengkap 4 tahap kompilasi
├── PENJELASAN.md      # Dokumen penjelasan ini
```

## 6. Kesimpulan

Program ini berhasil merepresentasikan keempat tahapan utama kompilasi — leksikal,
sintaksis, semantik, dan generasi kode antara (TAC) — untuk konstruksi perulangan
`for`. Pemisahan setiap tahap ke dalam kelas/fungsi tersendiri (`tokenize`, `Parser`,
`SemanticAnalyzer`, `TACGenerator`) mencerminkan arsitektur *compiler pipeline* yang
sesungguhnya, di mana keluaran satu tahap menjadi masukan bagi tahap berikutnya.
