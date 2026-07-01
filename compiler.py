"""
 Tugas UAS - Representasi Tahapan Kompilasi
 Konstruksi yang diimplementasikan : PERULANGAN (for-loop)
 Tahapan yang direpresentasikan   :
     1. Analisis Leksikal   (Lexer)
     2. Analisis Sintaksis  (Parser -> Abstract Syntax Tree)
     3. Analisis Semantik   (SemanticAnalyzer)
     4. Generasi Kode Antara (Three-Address Code / TAC)

"""

import re
import sys


# 1. ANALISIS LEKSIKAL (LEXER)

class Token:
    def __init__(self, type_, value, pos):
        self.type = type_
        self.value = value
        self.pos = pos

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"


# Daftar pola token, urutan penting (paling spesifik di atas)
TOKEN_SPECIFICATION = [
    ("SKIP",       r"[ \t\n]+"),
    ("COMMENT",    r"//[^\n]*"),
    ("TYPE",       r"\bint\b"),
    ("FOR",        r"\bfor\b"),
    ("NUMBER",     r"\d+(\.\d+)?"),
    ("ID",         r"[A-Za-z_][A-Za-z0-9_]*"),
    ("RELOP",      r"==|!=|<=|>=|<|>"),
    ("ASSIGN",     r"="),
    ("PLUS",       r"\+"),
    ("MINUS",      r"-"),
    ("TIMES",      r"\*"),
    ("DIVIDE",     r"/"),
    ("LPAREN",     r"\("),
    ("RPAREN",     r"\)"),
    ("LBRACE",     r"\{"),
    ("RBRACE",     r"\}"),
    ("SEMI",       r";"),
]

MASTER_PATTERN = "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPECIFICATION)
MASTER_RE = re.compile(MASTER_PATTERN)


class LexicalError(Exception):
    pass


def tokenize(source_code: str):
    """Memecah source code menjadi daftar token (Analisis Leksikal)."""
    tokens = []
    pos = 0
    length = len(source_code)
    while pos < length:
        match = MASTER_RE.match(source_code, pos)
        if not match:
            raise LexicalError(f"Karakter tidak dikenal pada posisi {pos}: {source_code[pos]!r}")
        kind = match.lastgroup
        value = match.group()
        if kind not in ("SKIP", "COMMENT"):
            tokens.append(Token(kind, value, pos))
        pos = match.end()
    tokens.append(Token("EOF", None, pos))
    return tokens


# 2. ANALISIS SINTAKSIS (PARSER -> AST)

# ---- Node-node AST ----
class Node:
    pass


class Program(Node):
    def __init__(self, statements):
        self.statements = statements


class VarDecl(Node):
    def __init__(self, var_type, name, expr):
        self.var_type = var_type
        self.name = name
        self.expr = expr


class Assign(Node):
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr


class BinOp(Node):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right


class Var(Node):
    def __init__(self, name):
        self.name = name


class Num(Node):
    def __init__(self, value):
        self.value = value


class ForLoop(Node):
    def __init__(self, init, condition, update, body):
        self.init = init            # Assign
        self.condition = condition  # BinOp (relasional)
        self.update = update        # Assign
        self.body = body            # list of statements


class SyntaxErrorCustom(Exception):
    pass


class Parser:
    """Recursive-descent parser sederhana."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos]

    def eat(self, type_):
        tok = self.current()
        if tok.type != type_:
            raise SyntaxErrorCustom(
                f"Diharapkan token {type_}, tetapi ditemukan {tok.type} ({tok.value!r}) "
                f"pada posisi {tok.pos}"
            )
        self.pos += 1
        return tok

    def parse_program(self):
        statements = []
        while self.current().type != "EOF":
            statements.append(self.parse_statement())
        return Program(statements)

    def parse_statement(self):
        tok = self.current()
        if tok.type == "TYPE":
            return self.parse_var_decl()
        elif tok.type == "FOR":
            return self.parse_for()
        elif tok.type == "ID":
            return self.parse_assign()
        else:
            raise SyntaxErrorCustom(f"Statement tidak dikenali mulai token {tok}")

    def parse_var_decl(self):
        self.eat("TYPE")
        name = self.eat("ID").value
        self.eat("ASSIGN")
        expr = self.parse_expr()
        self.eat("SEMI")
        return VarDecl("int", name, expr)

    def parse_assign(self, require_semi=True):
        name = self.eat("ID").value
        self.eat("ASSIGN")
        expr = self.parse_expr()
        if require_semi:
            self.eat("SEMI")
        return Assign(name, expr)

    def parse_for(self):
        self.eat("FOR")
        self.eat("LPAREN")
        init = self.parse_assign(require_semi=False)
        self.eat("SEMI")
        condition = self.parse_condition()
        self.eat("SEMI")
        update = self.parse_assign(require_semi=False)
        self.eat("RPAREN")
        self.eat("LBRACE")
        body = []
        while self.current().type != "RBRACE":
            body.append(self.parse_statement())
        self.eat("RBRACE")
        return ForLoop(init, condition, update, body)

    def parse_condition(self):
        left = self.parse_expr()
        op = self.eat("RELOP").value
        right = self.parse_expr()
        return BinOp(op, left, right)

    # <expr> ::= <term> (("+" | "-") <term>)*
    def parse_expr(self):
        node = self.parse_term()
        while self.current().type in ("PLUS", "MINUS"):
            op_tok = self.eat(self.current().type)
            right = self.parse_term()
            node = BinOp(op_tok.value, node, right)
        return node

    # <term> ::= <factor> (("*" | "/") <factor>)*
    def parse_term(self):
        node = self.parse_factor()
        while self.current().type in ("TIMES", "DIVIDE"):
            op_tok = self.eat(self.current().type)
            right = self.parse_factor()
            node = BinOp(op_tok.value, node, right)
        return node

    def parse_factor(self):
        tok = self.current()
        if tok.type == "NUMBER":
            self.eat("NUMBER")
            return Num(tok.value)
        elif tok.type == "ID":
            self.eat("ID")
            return Var(tok.value)
        elif tok.type == "LPAREN":
            self.eat("LPAREN")
            node = self.parse_expr()
            self.eat("RPAREN")
            return node
        else:
            raise SyntaxErrorCustom(f"Faktor tidak valid pada token {tok}")


# 3. ANALISIS SEMANTIK

class SemanticError(Exception):
    pass


class SemanticAnalyzer:
    """
    Melakukan pengecekan dasar:
      - Variabel harus dideklarasikan (dengan 'int') sebelum dipakai.
      - Tidak boleh ada deklarasi ganda untuk variabel yang sama.
      - Variabel yang dipakai di kondisi / update / body harus sudah ada
        di symbol table (baik dari deklarasi luar maupun dari init loop).
    """

    def __init__(self):
        self.symbol_table = {}  # nama_variabel -> tipe

    def analyze(self, program: Program):
        for stmt in program.statements:
            self.visit(stmt)
        return self.symbol_table

    def visit(self, node):
        method_name = f"visit_{type(node).__name__}"
        return getattr(self, method_name)(node)

    def visit_VarDecl(self, node: VarDecl):
        if node.name in self.symbol_table:
            raise SemanticError(f"Variabel '{node.name}' sudah dideklarasikan sebelumnya.")
        self.visit_expr(node.expr)
        self.symbol_table[node.name] = node.var_type

    def visit_Assign(self, node: Assign):
        if node.name not in self.symbol_table:
            raise SemanticError(f"Variabel '{node.name}' digunakan sebelum dideklarasikan.")
        self.visit_expr(node.expr)

    def visit_ForLoop(self, node: ForLoop):
        # variabel kontrol loop dianggap perlu sudah dideklarasikan
        if node.init.name not in self.symbol_table:
            raise SemanticError(
                f"Variabel kontrol loop '{node.init.name}' belum dideklarasikan "
                f"(gunakan 'int {node.init.name} = ...;' sebelum loop)."
            )
        self.visit_expr(node.init.expr)
        self.visit_expr(node.condition)
        if node.update.name not in self.symbol_table:
            raise SemanticError(f"Variabel '{node.update.name}' pada update belum dideklarasikan.")
        self.visit_expr(node.update.expr)

        for stmt in node.body:
            self.visit(stmt)

    def visit_expr(self, node):
        if isinstance(node, Num):
            return "int"
        elif isinstance(node, Var):
            if node.name not in self.symbol_table:
                raise SemanticError(f"Variabel '{node.name}' belum dideklarasikan.")
            return self.symbol_table[node.name]
        elif isinstance(node, BinOp):
            left_type = self.visit_expr(node.left)
            right_type = self.visit_expr(node.right)
            if left_type != right_type:
                raise SemanticError(
                    f"Ketidakcocokan tipe pada operasi '{node.op}': {left_type} vs {right_type}"
                )
            return left_type
        else:
            raise SemanticError(f"Ekspresi tidak dikenal: {node}")


# 4. GENERASI KODE ANTARA (THREE-ADDRESS CODE)

class TACGenerator:
    def __init__(self):
        self.code = []
        self.temp_count = 0
        self.label_count = 0

    def new_temp(self):
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self):
        self.label_count += 1
        return f"L{self.label_count}"

    def emit(self, line):
        self.code.append(line)

    def generate(self, program: Program):
        for stmt in program.statements:
            self.visit(stmt)
        return self.code

    def visit(self, node):
        method_name = f"visit_{type(node).__name__}"
        return getattr(self, method_name)(node)

    def visit_VarDecl(self, node: VarDecl):
        value = self.visit_expr(node.expr)
        self.emit(f"{node.name} = {value}")

    def visit_Assign(self, node: Assign):
        value = self.visit_expr(node.expr)
        self.emit(f"{node.name} = {value}")

    def visit_ForLoop(self, node: ForLoop):
        # 1) inisialisasi
        init_value = self.visit_expr(node.init.expr)
        self.emit(f"{node.init.name} = {init_value}")

        label_start = self.new_label()
        label_end = self.new_label()

        # 2) label awal loop + pengecekan kondisi (pola: while)
        self.emit(f"{label_start}:")
        cond_temp = self.visit_expr(node.condition)
        self.emit(f"ifFalse {cond_temp} goto {label_end}")

        # 3) badan loop
        for stmt in node.body:
            self.visit(stmt)

        # 4) update, lalu lompat balik ke label awal
        update_value = self.visit_expr(node.update.expr)
        self.emit(f"{node.update.name} = {update_value}")
        self.emit(f"goto {label_start}")
        self.emit(f"{label_end}:")

    def visit_expr(self, node):
        """Mengembalikan 'alamat' (nama variabel/konstanta/temp) dari sebuah ekspresi."""
        if isinstance(node, Num):
            return node.value
        elif isinstance(node, Var):
            return node.name
        elif isinstance(node, BinOp):
            left = self.visit_expr(node.left)
            right = self.visit_expr(node.right)
            temp = self.new_temp()
            self.emit(f"{temp} = {left} {node.op} {right}")
            return temp
        else:
            raise Exception(f"Node ekspresi tidak dikenal saat generate TAC: {node}")


# PROGRAM UTAMA

def print_ast(node, indent=0):
    """Utility kecil untuk mencetak AST secara terbaca (pretty-print)."""
    pad = "  " * indent
    if isinstance(node, Program):
        print(f"{pad}Program")
        for s in node.statements:
            print_ast(s, indent + 1)
    elif isinstance(node, VarDecl):
        print(f"{pad}VarDecl(type=int, name={node.name})")
        print_ast(node.expr, indent + 1)
    elif isinstance(node, Assign):
        print(f"{pad}Assign(name={node.name})")
        print_ast(node.expr, indent + 1)
    elif isinstance(node, ForLoop):
        print(f"{pad}ForLoop")
        print(f"{pad}  init:")
        print_ast(node.init, indent + 2)
        print(f"{pad}  condition:")
        print_ast(node.condition, indent + 2)
        print(f"{pad}  update:")
        print_ast(node.update, indent + 2)
        print(f"{pad}  body:")
        for s in node.body:
            print_ast(s, indent + 2)
    elif isinstance(node, BinOp):
        print(f"{pad}BinOp(op={node.op})")
        print_ast(node.left, indent + 1)
        print_ast(node.right, indent + 1)
    elif isinstance(node, Var):
        print(f"{pad}Var({node.name})")
    elif isinstance(node, Num):
        print(f"{pad}Num({node.value})")


def compile_source(source_code: str, verbose: bool = True):
    """Menjalankan seluruh pipeline kompilasi terhadap source_code."""

    if verbose:
        print("=" * 70)
        print("SOURCE CODE")
        print("=" * 70)
        print(source_code.strip())

    # 1. Leksikal
    tokens = tokenize(source_code)
    if verbose:
        print("\n" + "=" * 70)
        print("TAHAP 1: ANALISIS LEKSIKAL (TOKEN)")
        print("=" * 70)
        for tok in tokens:
            if tok.type != "EOF":
                print(f"  {tok.type:<8} : {tok.value}")

    # 2. Sintaksis
    parser = Parser(tokens)
    ast = parser.parse_program()
    if verbose:
        print("\n" + "=" * 70)
        print("TAHAP 2: ANALISIS SINTAKSIS (ABSTRACT SYNTAX TREE)")
        print("=" * 70)
        print_ast(ast)

    # 3. Semantik
    analyzer = SemanticAnalyzer()
    symbol_table = analyzer.analyze(ast)
    if verbose:
        print("\n" + "=" * 70)
        print("TAHAP 3: ANALISIS SEMANTIK (SYMBOL TABLE)")
        print("=" * 70)
        for name, type_ in symbol_table.items():
            print(f"  {name} : {type_}")
        print("  (Semua variabel valid, tidak ada error tipe/deklarasi)")

    # 4. Generasi Kode (TAC)
    tac_gen = TACGenerator()
    tac_code = tac_gen.generate(ast)
    if verbose:
        print("\n" + "=" * 70)
        print("TAHAP 4: GENERASI THREE-ADDRESS CODE (TAC)")
        print("=" * 70)
        for line in tac_code:
            print(f"  {line}")

    return tokens, ast, symbol_table, tac_code


if __name__ == "__main__":
    # --- Contoh 1: source code valid ---
    contoh_source = """
    int i = 0;
    int total = 0;
    int y = 0;
    for (i = 0; i < 5; i = i + 1) {
        total = total + i;
        y = i * 2;
    }
    """

    try:
        compile_source(contoh_source)
    except (LexicalError, SyntaxErrorCustom, SemanticError) as e:
        print(f"\n[GAGAL KOMPILASI] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Contoh 2: source code dengan error semantik (variabel belum dideklarasikan) ---
    print("\n\n" + "#" * 70)
    print("# DEMO PENANGANAN ERROR SEMANTIK")
    print("#" * 70)
    contoh_error = """
    int i = 0;
    for (i = 0; i < 5; i = i + 1) {
        z = z + 1;
    }
    """
    try:
        compile_source(contoh_error)
    except (LexicalError, SyntaxErrorCustom, SemanticError) as e:
        print(f"\n[GAGAL KOMPILASI - SESUAI EKSPEKTASI] {type(e).__name__}: {e}")
