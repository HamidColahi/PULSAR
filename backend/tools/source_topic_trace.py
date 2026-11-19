# Pulsar/backend/tools/source_topic_trace.py
"""
PULSAR Source Topic Tracer
Static repository-wide source discovery and relationship tracing.

Supported languages:
- Python
- JavaScript / JSX
- TypeScript / TSX
- Vue
- SQL

Usage:
    python tools/source_topic_trace.py . "Grid Ownership"
    python tools/source_topic_trace.py . "profile_id" --json
    python tools/source_topic_trace.py . "profile_id" --summary
    python tools/source_topic_trace.py . "profile_id" --scope backend database
    python tools/source_topic_trace.py . "profile_id" --relations references calls
    python tools/source_topic_trace.py . "profile_id" --depth 4 --edges

Static analysis discovers likely source relationships. It does not prove
runtime execution. Dynamic dispatch, reflection, generated code, and database
behavior may require runtime instrumentation or manual verification.

Modified: 2026-11-19 (Asia/Baku)
Version: 6.7

In collaboration with GPT4 Chat Assistant: Bahram
"""

from __future__ import annotations

import argparse
import ast
import builtins
import json
import re

from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


SUPPORTED = {".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".sql"}

SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    "dist", "build", ".next", ".nuxt", "coverage",
    ".pytest_cache", ".mypy_cache",
}

SCOPE_EXTENSIONS = {
    "frontend": {".js", ".jsx", ".ts", ".tsx", ".vue"},
    "backend": {".py"},
    "database": {".sql"},
}

VALID_SCOPES = set(SCOPE_EXTENSIONS)
VALID_RELATIONS = {"calls", "imports", "api", "references", "sql"}

IDENTIFIER = re.compile(r"[A-Za-z_$][\w$]*")

JS_IMPORT = re.compile(
    r"""^\s*import\s+(?:(.*?)\s+from\s+)?['"]([^'"]+)['"]""",
    re.M,
)

JS_FUNCTION = re.compile(
    r"""
    (?:export\s+)?
    (?:default\s+)?
    (?:async\s+)?
    function\s+([A-Za-z_$][\w$]*)\s*\(
    """,
    re.X,
)

JS_ARROW = re.compile(
    r"""
    (?:export\s+)?
    (?:default\s+)?
    (?:async\s+)?
    (?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*
    (?:async\s*)?
    (?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=> 
    """,
    re.X,
)

JS_CALL = re.compile(r"\b([A-Za-z_$][\w$]*)\s*\(")
VUE_COMPONENT = re.compile(r"<([A-Z][A-Za-z0-9_]*)\b")

API_PATH = re.compile(
    r"""(?:url|path|endpoint)\s*[:=]\s*['"`]([^'"`]+)['"`]""",
    re.I,
)

API_METHOD = re.compile(
    r"""method\s*[:=]\s*['"`](GET|POST|PUT|PATCH|DELETE)['"`]""",
    re.I,
)

ROUTE_DECORATOR = re.compile(
    r"""@(?:router|app)\.(get|post|put|patch|delete)\s*\(\s*['"]([^'"]+)['"]""",
    re.I,
)

SQL_OBJECT = re.compile(
    r"""
    \b(?:from|join|update|into|table|references|
    truncate\s+table|alter\s+table|drop\s+table)
    \s+
    ([A-Za-z_][\w$]*(?:\.[A-Za-z_][\w$]*)?)
    """,
    re.I | re.X,
)

SQL_DEFINITION = re.compile(
    r"""
    \bcreate\s+
    (?:or\s+replace\s+)?
    (?:temporary\s+|temp\s+)?
    (?:table|view|materialized\s+view|
    function|procedure|sequence)
    \s+
    (?:if\s+not\s+exists\s+)?
    ([A-Za-z_][\w$]*(?:\.[A-Za-z_][\w$]*)?)
    """,
    re.I | re.X,
)

PYTHON_BUILTINS = set(dir(builtins))

JS_KEYWORDS = {
    "async", "await", "break", "case", "catch", "class", "const",
    "continue", "debugger", "default", "delete", "do", "else",
    "export", "extends", "false", "finally", "for", "from",
    "function", "if", "import", "in", "instanceof", "let", "new",
    "null", "return", "static", "super", "switch", "this", "throw",
    "true", "try", "typeof", "undefined", "var", "void", "while",
    "with", "yield", "of", "get", "set", "implements", "interface",
    "package", "private", "protected", "public", "enum", "declare",
    "type", "as", "satisfies", "keyof",
}

COMMON_TOPIC_WORDS = {
    "the", "and", "for", "from", "with", "that", "this", "into",
    "when", "where", "what", "which", "how", "is", "are", "was",
    "were", "be", "has", "have", "does", "do", "not", "all",
    "any", "can", "may",
}


@dataclass
class SourceNode:
    id: str
    file: str
    line: int
    kind: str
    name: str
    language: str
    excerpt: str = ""
    tags: list[str] = field(default_factory=list)
    end_line: int = 0
    depth: int | None = None


@dataclass
class SourceEdge:
    source: str
    target: str
    relation: str
    confidence: str
    evidence: str = ""
    graph: str = "structural"


class TopicTracer:

    def __init__(self, repository: str | Path):
        self.root = Path(repository).expanduser().resolve()

        if not self.root.is_dir():
            raise NotADirectoryError(
                f"Repository directory not found: {self.root}"
            )

        self._reset()

    def _reset(self) -> None:
        self.nodes: dict[str, SourceNode] = {}
        self.edges: list[SourceEdge] = []
        self.edge_keys: set[tuple[str, str, str, str]] = set()

        self.file_text: dict[str, str] = {}
        self.file_lines: dict[str, list[str]] = {}
        self.file_nodes: dict[str, str] = {}

        self.symbols: dict[tuple[str, str], list[str]] = defaultdict(list)
        self.file_imports: dict[str, list[dict]] = defaultdict(list)
        self.imported_symbols: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )

        self.pending_calls: list[dict] = []
        self.reference_parent: dict[str, str] = {}
        self.reference_owners: list[tuple[str, str]] = []
        self.pending_api_handlers: list[dict] = []
        self.router_prefixes: dict[tuple[str, str], str] = {}
        self.model_tables: dict[tuple[str, str], str] = {}
        self.model_class_nodes: dict[tuple[str, str], str] = {}
        self.model_table_nodes: dict[tuple[str, str], str] = {}
        self.model_column_nodes: dict[tuple[str, str, str], str] = {}
        self.pending_orm_references: list[dict] = []
        self.pending_model_references: list[dict] = []
        self.pending_model_aliases: list[dict] = []
        self.model_aliases: dict[tuple[str, str, str], str] = {}
        self.pending_foreign_keys: list[dict] = []
        self.imported_symbol_names: dict[str, dict[str, str]] = defaultdict(dict)
        self.match_candidates: list[dict] = []

    @staticmethod
    def _language(file: str) -> str:
        suffix = Path(file).suffix.lower()

        if suffix == ".py":
            return "python"
        if suffix == ".sql":
            return "sql"
        return "javascript"

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def _read_sources(self) -> None:
        for path in sorted(self.root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED:
                continue

            relative_path = path.relative_to(self.root)

            if any(part in SKIP_DIRS for part in relative_path.parts):
                continue

            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue

            relative = self._relative(path)
            self.file_text[relative] = content
            self.file_lines[relative] = content.splitlines()

    def _add_node(
        self,
        file: str,
        line: int,
        kind: str,
        name: str,
        excerpt: str = "",
        tags: Iterable[str] = (),
        end_line: int = 0,
    ) -> str:
        language = self._language(file)
        node_id = f"{file}:{line}:{kind}:{name}"

        if node_id not in self.nodes:
            self.nodes[node_id] = SourceNode(
                id=node_id,
                file=file,
                line=line,
                kind=kind,
                name=name,
                language=language,
                excerpt=excerpt.strip()[:500],
                tags=sorted(set(tags)),
                end_line=end_line or line,
            )

            if kind in {"function", "class"}:
                self.symbols[(language, name.split(".")[-1])].append(node_id)

        return node_id

    def _add_edge(
        self,
        source: str | None,
        target: str | None,
        relation: str,
        confidence: str,
        evidence: str = "",
        graph: str = "structural",
    ) -> None:
        if not source or not target or source == target:
            return
        if source not in self.nodes or target not in self.nodes:
            return

        key = (source, target, relation, graph)
        if key in self.edge_keys:
            return

        self.edge_keys.add(key)
        self.edges.append(
            SourceEdge(source, target, relation, confidence, evidence, graph)
        )

    @staticmethod
    def _tags_for(text: str, file: str) -> list[str]:
        low = text.lower()
        tags = []

        rules = {
            "frontend": (
                "vue", "component", "router.push", "axios",
                "fetch(", "emit(", "usecomponent",
            ),
            "api": (
                "api", "http", "endpoint", "router.get",
                "router.post", "@router",
            ),
            "authentication": (
                "get_current_user", "current_user", "jwt",
                "token", "authenticate",
            ),
            "database": (
                "select ", "insert ", "update ", "delete ",
                "session.", "execute(", "sqlalchemy",
            ),
            "metadata": (
                "metadata", "where_clause", "components_base",
                "dynamic_components",
            ),
            "ownership": (
                "profile_id", "owner", "ownership",
                "selected_record", "runtime_context",
            ),
            "navigation": (
                "router.push", "route.query", "navigate",
                "selected_record", "context_panel",
            ),
        }

        for tag, needles in rules.items():
            if tag in {"frontend", "backend"}:
                continue
            if any(needle in low for needle in needles):
                tags.append(tag)

        suffix = Path(file).suffix.lower()
        if suffix == ".py":
            tags.append("backend")
        elif suffix == ".sql":
            tags.append("database")
        else:
            tags.append("frontend")

        return sorted(set(tags))

    def _add_reference(
        self,
        file: str,
        line: int,
        name: str,
        excerpt: str,
        owner_id: str | None = None,
        confidence: str = "structural",
    ) -> str:
        if not name or len(name) < 2:
            return ""

        node_id = self._add_node(
            file, line, "identifier_reference", name,
            excerpt, self._tags_for(excerpt, file),
        )

        if owner_id:
            self.reference_parent[node_id] = owner_id
            self._add_edge(
                owner_id,
                node_id,
                "references",
                confidence,
                f"{file}:{line} references {name}",
            )
        else:
            self.reference_owners.append((file, node_id))

        return node_id

    def _index_python_api(self, file: str, text: str) -> None:
        """Index FastAPI route declarations and connect them to handler functions."""
        lines = text.splitlines()
        prefixes = {}

        router_pattern = re.compile(
            r"""([A-Za-z_]\w*)\s*=\s*APIRouter\s*\([^)]*?prefix\s*=\s*['"]([^'"]*)['"]""",
            re.S,
        )
        for match in router_pattern.finditer(text):
            prefixes[match.group(1)] = match.group(2)

        include_pattern = re.compile(
            r"""include_router\s*\(\s*([A-Za-z_]\w*)\s*,\s*[^)]*?prefix\s*=\s*['"]([^'"]*)['"]""",
            re.S,
        )
        for match in include_pattern.finditer(text):
            router_name, prefix = match.groups()
            prefixes[router_name] = prefix.rstrip("/") + prefixes.get(router_name, "")

        decorator_pattern = re.compile(
            r"""@([A-Za-z_]\w*)\.(get|post|put|patch|delete)\s*\(\s*['"]([^'"]*)['"]""",
            re.I,
        )
        functions = [
            node for node in self.nodes.values()
            if node.file == file and node.kind == "function"
        ]

        for match in decorator_pattern.finditer(text):
            router_name, method, route = match.groups()
            line = self._line_number(text, match.start())
            prefix = prefixes.get(router_name, "")
            full_route = self._normalize_route(prefix + "/" + route.lstrip("/"))
            endpoint_id = self._add_node(
                file, line, "api_endpoint", f"{method.upper()} {full_route}",
                lines[line - 1] if line <= len(lines) else "",
                ["api", "backend"],
            )
            handlers = [
                node for node in functions
                if node.line >= line and node.line - line <= 8
            ]
            if handlers:
                handler = min(handlers, key=lambda node: node.line)
                self._add_edge(
                    endpoint_id, handler.id, "api", "decorator_to_handler",
                    f"{file}:{line} declares {method.upper()} {full_route}",
                )

    def _index_python_models(self, file: str, text: str) -> None:
        """Index SQLAlchemy models, mapped columns, and declared foreign keys."""
        try:
            tree = ast.parse(text, filename=file)
        except SyntaxError:
            return

        def call_name(node: ast.AST) -> str:
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Attribute):
                return node.attr
            return ""

        def string_constants(node: ast.AST) -> list[str]:
            return [
                item.value for item in ast.walk(node)
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            ]

        for class_node in (item for item in ast.walk(tree) if isinstance(item, ast.ClassDef)):
            table_name = None
            for child in class_node.body:
                if isinstance(child, (ast.Assign, ast.AnnAssign)):
                    targets = child.targets if isinstance(child, ast.Assign) else [child.target]
                    if any(isinstance(target, ast.Name) and target.id == "__tablename__" for target in targets):
                        value = child.value
                        if isinstance(value, ast.Constant) and isinstance(value.value, str):
                            table_name = value.value
                            break
            if not table_name:
                continue

            class_id = next(
                (item.id for item in self.nodes.values()
                 if item.file == file and item.kind == "class"
                 and item.name.split(".")[-1] == class_node.name),
                None,
            )
            if not class_id:
                continue

            table_id = self._add_node(
                file, class_node.lineno, "database_object_definition", table_name,
                ast.get_source_segment(text, class_node) or class_node.name,
                ["database", "backend"],
                getattr(class_node, "end_lineno", class_node.lineno),
            )
            model_key = (file, class_node.name)
            self.model_tables[model_key] = table_name
            self.model_class_nodes[model_key] = class_id
            self.model_table_nodes[model_key] = table_id
            self._add_edge(
                class_id, table_id, "sql", "sqlalchemy_tablename",
                f"{file}:{class_node.lineno} maps {class_node.name} to {table_name}",
            )

            for member in class_node.body:
                if not isinstance(member, (ast.Assign, ast.AnnAssign)):
                    continue
                targets = member.targets if isinstance(member, ast.Assign) else [member.target]
                target_names = [target.id for target in targets if isinstance(target, ast.Name)]
                if not target_names or member.value is None:
                    continue

                calls = [item for item in ast.walk(member.value) if isinstance(item, ast.Call)]
                column_call = next(
                    (item for item in calls if call_name(item.func) in {"Column", "mapped_column"}),
                    None,
                )
                if column_call is None:
                    continue

                column_name = target_names[0]
                if column_call.args:
                    first_arg = column_call.args[0]
                    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                        column_name = first_arg.value

                column_id = self._add_node(
                    file, member.lineno, "database_column_definition", column_name,
                    ast.get_source_segment(text, member) or column_name,
                    ["database", "backend"],
                    getattr(member, "end_lineno", member.lineno),
                )
                self.model_column_nodes[(file, class_node.name, target_names[0])] = column_id
                self.model_column_nodes[(file, class_node.name, column_name)] = column_id
                self._add_edge(
                    table_id, column_id, "sql", "sqlalchemy_column",
                    f"{class_node.name}.{column_name} belongs to {table_name}",
                )

                for nested_call in calls:
                    if call_name(nested_call.func) != "ForeignKey":
                        continue
                    if not nested_call.args:
                        continue
                    fk_values = string_constants(nested_call.args[0])
                    if not fk_values:
                        continue
                    self.pending_foreign_keys.append({
                        "source": column_id,
                        "file": file,
                        "model": class_node.name,
                        "column": column_name,
                        "target": fk_values[0],
                        "line": nested_call.lineno,
                    })


            # Index composite ForeignKeyConstraint declarations.
            for member in class_node.body:
                if not isinstance(member, (ast.Assign, ast.AnnAssign)):
                    continue

                value = member.value
                if value is None:
                    continue

                for constraint_call in (
                    item for item in ast.walk(value)
                    if isinstance(item, ast.Call)
                    and call_name(item.func) == "ForeignKeyConstraint"
                ):
                    if len(constraint_call.args) < 2:
                        continue

                    try:
                        source_columns = ast.literal_eval(
                            constraint_call.args[0]
                        )
                        target_columns = ast.literal_eval(
                            constraint_call.args[1]
                        )
                    except (ValueError, TypeError, SyntaxError):
                        continue

                    if not (
                        isinstance(source_columns, (list, tuple))
                        and isinstance(target_columns, (list, tuple))
                        and len(source_columns) == len(target_columns)
                        and source_columns
                        and all(isinstance(item, str) for item in source_columns)
                        and all(isinstance(item, str) for item in target_columns)
                    ):
                        continue

                    self.pending_foreign_keys.append({
                        "kind": "composite",
                        "file": file,
                        "model": class_node.name,
                        "source_columns": list(source_columns),
                        "target_columns": list(target_columns),
                        "line": constraint_call.lineno,
                    })


    def _index_embedded_sql(
        self,
        file: str,
        sql: str,
        line: int,
        owner_id: str | None,
    ) -> None:
        """Index SQL statements embedded in Python source."""
        if not sql or not re.search(
            r"\b(select|insert|update|delete|with)\b",
            sql,
            re.I,
        ):
            return

        statement_id = self._add_node(
            file,
            line,
            "sql_statement",
            f"SQL statement at line {line}",
            sql.strip()[:1200],
            ["database", "backend"],
            line + sql.count("\n"),
        )

        if owner_id:
            self._add_edge(
                owner_id,
                statement_id,
                "sql",
                "python_embedded_sql",
                f"{file}:{line} executes embedded SQL",
            )

        reserved = {
            "where", "on", "left", "right", "inner", "outer",
            "cross", "full", "join", "group", "order", "having",
            "limit", "offset", "union", "except", "intersect",
            "set", "values", "returning", "for", "when",
        }

        table_pattern = re.compile(
            r"""
            \b(?:FROM|JOIN|UPDATE|INTO|REFERENCES)
            \s+
            ([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)
            (?:\s+(?:AS\s+)?([A-Za-z_]\w*))?
            """,
            re.I | re.X,
        )

        aliases = {}
        table_nodes = {}

        for match in table_pattern.finditer(sql):
            table_name = match.group(1)
            alias = match.group(2)

            if alias and alias.lower() in reserved:
                alias = None

            object_line = line + sql.count("\n", 0, match.start())

            table_id = self._add_node(
                file,
                object_line,
                "database_object_reference",
                table_name,
                match.group(0).strip(),
                ["database", "backend"],
            )

            self._add_edge(
                statement_id,
                table_id,
                "sql",
                "embedded_sql_object",
                f"SQL references {table_name}",
            )

            table_nodes[table_name] = table_id

            if alias:
                aliases[alias] = table_name
            aliases.setdefault(table_name.split(".")[-1], table_name)

        column_pattern = re.compile(
            r"\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\b"
        )

        for match in column_pattern.finditer(sql):
            alias, column_name = match.groups()
            table_name = aliases.get(alias)

            if not table_name:
                continue

            table_id = table_nodes.get(table_name)
            if not table_id:
                continue

            column_line = line + sql.count("\n", 0, match.start())

            column_id = self._add_node(
                file,
                column_line,
                "database_column_reference",
                f"{table_name}.{column_name}",
                match.group(0),
                ["database", "backend"],
            )

            self._add_edge(
                table_id,
                column_id,
                "sql",
                "embedded_sql_column",
                f"{alias}.{column_name} resolves to {table_name}.{column_name}",
            )



    def _index_python(self, file: str, text: str) -> None:
        try:
            tree = ast.parse(text, filename=file)
        except SyntaxError:
            return

        tracer = self

        class Visitor(ast.NodeVisitor):

            def __init__(self):
                self.scope: list[str] = []
                self.functions: list[str] = []

            def visit_Import(self, node):
                for alias in node.names:
                    local = alias.asname or alias.name.split(".")[0]
                    tracer.file_imports[file].append({
                        "module": alias.name,
                        "line": node.lineno,
                        "bindings": {local: alias.name.split(".")[-1]},
                    })

            def visit_ImportFrom(self, node):
                if not node.module:
                    return

                bindings = {
                    alias.asname or alias.name: alias.name
                    for alias in node.names
                    if alias.name != "*"
                }

                tracer.file_imports[file].append({
                    "module": "." * node.level + node.module,
                    "line": node.lineno,
                    "bindings": bindings,
                })

            def visit_FunctionDef(self, node):
                self._visit_function(node)

            def visit_AsyncFunctionDef(self, node):
                self._visit_function(node)

            def _visit_function(self, node):
                qualified = ".".join(self.scope + [node.name])
                excerpt = ast.get_source_segment(text, node) or node.name

                function_id = tracer._add_node(
                    file,
                    node.lineno,
                    "function",
                    qualified,
                    excerpt,
                    tracer._tags_for(excerpt, file),
                    getattr(node, "end_lineno", node.lineno),
                )

                self.scope.append(node.name)
                self.functions.append(function_id)

                for child in node.body:
                    self.visit(child)

                self.functions.pop()
                self.scope.pop()

            def visit_ClassDef(self, node):
                qualified = ".".join(self.scope + [node.name])
                excerpt = ast.get_source_segment(text, node) or node.name

                tracer._add_node(
                    file,
                    node.lineno,
                    "class",
                    qualified,
                    excerpt,
                    tracer._tags_for(excerpt, file),
                    getattr(node, "end_lineno", node.lineno),
                )

                self.scope.append(node.name)
                for child in node.body:
                    self.visit(child)
                self.scope.pop()

            def _record_model_alias(self, target, value, owner_id):
                if not isinstance(target, ast.Name):
                    return
                model_name = None
                if isinstance(value, ast.Name):
                    model_name = value.id
                elif isinstance(value, ast.Call):
                    called = self._call_name(value.func) or ""
                    if called.split(".")[-1] in {"aliased", "with_polymorphic"}:
                        model_arg = next(
                            (arg for arg in value.args if isinstance(arg, ast.Name)),
                            None,
                        )
                        if model_arg:
                            model_name = model_arg.id
                if model_name and owner_id:
                    tracer.pending_model_aliases.append({
                        "file": file,
                        "owner": owner_id,
                        "alias": target.id,
                        "model": model_name,
                        "line": getattr(target, "lineno", 0),
                    })

            def visit_Assign(self, node):
                owner = self.functions[-1] if self.functions else None
                for target in node.targets:
                    self._record_model_alias(target, node.value, owner)
                self.generic_visit(node)

            def visit_AnnAssign(self, node):
                owner = self.functions[-1] if self.functions else None
                if node.value is not None:
                    self._record_model_alias(node.target, node.value, owner)
                self.generic_visit(node)

            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Load):
                    line = node.lineno
                    source_line = (
                        tracer.file_lines[file][line - 1]
                        if line <= len(tracer.file_lines[file]) else ""
                    )
                    owner = self.functions[-1] if self.functions else None

                    if node.id not in PYTHON_BUILTINS:
                        tracer._add_reference(
                            file, line, node.id, source_line, owner,
                            "python_ast_name",
                        )
                        if owner:
                            tracer.pending_model_references.append({
                                "source": owner,
                                "file": file,
                                "name": node.id,
                                "member": None,
                                "line": line,
                                "evidence": source_line.strip(),
                            })

                self.generic_visit(node)

            def visit_Attribute(self, node):
                line = node.lineno
                source_line = (
                    tracer.file_lines[file][line - 1]
                    if line <= len(tracer.file_lines[file]) else ""
                )
                owner = self.functions[-1] if self.functions else None

                tracer._add_reference(
                    file, line, node.attr, source_line, owner,
                    "python_ast_attribute",
                )
                if owner and isinstance(node.value, ast.Name):
                    tracer.pending_model_references.append({
                        "source": owner,
                        "file": file,
                        "name": node.value.id,
                        "member": node.attr,
                        "line": line,
                        "evidence": source_line.strip(),
                    })
                self.generic_visit(node)

            def visit_Call(self, node):
                if self.functions:
                    called = self._call_name(node.func)

                    # Index literal SQL passed to text() or execute().
                    terminal = called.split(".")[-1] if called else ""

                    if terminal in {"text", "execute"} and node.args:
                        sql_argument = node.args[0]

                        if (
                            isinstance(sql_argument, ast.Constant)
                            and isinstance(sql_argument.value, str)
                        ):
                            tracer._index_embedded_sql(
                                file,
                                sql_argument.value,
                                getattr(sql_argument, "lineno", node.lineno),
                                self.functions[-1],
                            )

                    if called:
                        tracer.pending_calls.append({
                            "source": self.functions[-1],
                            "called": called,
                            "file": file,
                            "line": node.lineno,
                            "language": "python",
                        })

                    # Defer ORM argument classification until model declarations
                    # and imported symbols have been indexed.
                    terminal = called.split(".")[-1] if called else ""
                    if terminal in {
                        "select", "query", "DataWindowManager",
                        "update", "delete", "insert", "add",
                    }:
                        for argument in node.args:
                            if isinstance(argument, ast.Name):
                                tracer.pending_orm_references.append({
                                    "source": self.functions[-1],
                                    "file": file,
                                    "name": argument.id,
                                    "line": argument.lineno,
                                    "call": terminal,
                                    "call_line": node.lineno,
                                })
                self.generic_visit(node)

            @staticmethod
            def _call_name(node):
                if isinstance(node, ast.Name):
                    return node.id
                if isinstance(node, ast.Attribute):
                    parts = []
                    current = node
                    while isinstance(current, ast.Attribute):
                        parts.append(current.attr)
                        current = current.value
                    if isinstance(current, ast.Name):
                        parts.append(current.id)
                    return ".".join(reversed(parts))
                return None

        Visitor().visit(tree)
        self._index_python_models(file, text)
        self._index_python_api(file, text)

    @staticmethod
    def _mask_javascript(text: str) -> str:
        """Mask comments and quoted strings while preserving line positions."""
        chars = list(text)
        length = len(text)
        index = 0

        def mask(start: int, end: int) -> None:
            for pos in range(start, end):
                if chars[pos] not in "\r\n":
                    chars[pos] = " "

        while index < length:
            if text[index] in ("'", '"', "`"):
                quote = text[index]
                start = index
                index += 1

                while index < length:
                    if text[index] == "\\":
                        index += 2
                        continue
                    if text[index] == quote:
                        index += 1
                        break
                    index += 1

                mask(start, min(index, length))
                continue

            if text.startswith("//", index):
                start = index
                end = text.find("\n", index)
                if end == -1:
                    end = length
                mask(start, end)
                index = end
                continue

            if text.startswith("/*", index):
                start = index
                end = text.find("*/", index + 2)
                end = length if end == -1 else end + 2
                mask(start, end)
                index = end
                continue

            index += 1

        return "".join(chars)

    @staticmethod
    def _mask_sql(text: str) -> str:
        chars = list(text)
        index = 0
        length = len(text)

        def mask(start: int, end: int) -> None:
            for pos in range(start, end):
                if chars[pos] not in "\r\n":
                    chars[pos] = " "

        while index < length:
            if text.startswith("--", index):
                start = index
                end = text.find("\n", index)
                end = length if end == -1 else end
                mask(start, end)
                index = end
                continue

            if text.startswith("/*", index):
                start = index
                end = text.find("*/", index + 2)
                end = length if end == -1 else end + 2
                mask(start, end)
                index = end
                continue

            if text[index] in ("'", '"'):
                quote = text[index]
                start = index
                index += 1

                while index < length:
                    if text[index] == quote:
                        if index + 1 < length and text[index + 1] == quote:
                            index += 2
                            continue
                        index += 1
                        break
                    if text[index] == "\\":
                        index += 2
                    else:
                        index += 1

                mask(start, min(index, length))
                continue

            index += 1

        return "".join(chars)

    @staticmethod
    def _line_number(text: str, position: int) -> int:
        return text.count("\n", 0, position) + 1

    @staticmethod
    def _find_brace_end(text: str, opening: int) -> int:
        depth = 0
        for position in range(opening, len(text)):
            if text[position] == "{":
                depth += 1
            elif text[position] == "}":
                depth -= 1
                if depth == 0:
                    return position
        return min(len(text) - 1, opening + 5000)

    @staticmethod
    def _extract_js_bindings(value: str) -> dict[str, str]:
        bindings = {}

        named = re.search(r"\{([^}]+)\}", value)
        if named:
            for item in named.group(1).split(","):
                parts = item.strip().split()
                if not parts:
                    continue
                imported = parts[0]
                local = (
                    parts[-1]
                    if len(parts) > 1 and parts[-2] == "as"
                    else imported
                )
                bindings[local] = imported

        default = re.match(r"\s*([A-Za-z_$][\w$]*)", value)
        if default:
            bindings[default.group(1)] = "default"

        namespace = re.search(r"\*\s+as\s+([A-Za-z_$][\w$]*)", value)
        if namespace:
            bindings[namespace.group(1)] = "*"

        return bindings

    def _function_ranges(
        self,
        file: str,
        text: str,
        masked: str,
    ) -> list[tuple[int, int, str]]:
        lines = text.splitlines()
        ranges = []
        seen = set()

        for pattern in (JS_FUNCTION, JS_ARROW):
            for match in pattern.finditer(masked):
                name = match.group(1)
                start_line = self._line_number(text, match.start())

                opening = masked.find("{", match.end())
                if opening == -1:
                    end_line = min(len(lines), start_line + 1)
                else:
                    end = self._find_brace_end(masked, opening)
                    end_line = self._line_number(text, end)

                key = (name, start_line)
                if key in seen:
                    continue
                seen.add(key)

                excerpt = "\n".join(lines[start_line - 1:end_line])
                node_id = self._add_node(
                    file,
                    start_line,
                    "function",
                    name,
                    excerpt,
                    self._tags_for(excerpt, file),
                    end_line,
                )
                ranges.append((start_line, end_line, node_id))

        return ranges

    def _index_text_source(self, file: str, text: str) -> None:
        lines = text.splitlines()
        language = self._language(file)
        masked = self._mask_javascript(text)

        for match in JS_IMPORT.finditer(text):
            bindings_text, module = match.groups()
            self.file_imports[file].append({
                "module": module,
                "line": self._line_number(text, match.start()),
                "bindings": self._extract_js_bindings(bindings_text or ""),
            })

        function_ranges = []

        if language == "javascript":
            function_ranges = self._function_ranges(file, text, masked)

            for match in VUE_COMPONENT.finditer(masked):
                name = match.group(1)
                line = self._line_number(text, match.start())
                excerpt = lines[line - 1] if line <= len(lines) else ""

                self._add_node(
                    file, line, "component_usage", name,
                    excerpt, ["frontend"],
                )

            masked_lines = masked.splitlines()
            for start, end, owner_id in function_ranges:
                for line_no in range(start, min(end, len(lines)) + 1):
                    code_line = masked_lines[line_no - 1]
                    for call in JS_CALL.finditer(code_line):
                        called = call.group(1)
                        if called in JS_KEYWORDS:
                            continue
                        self.pending_calls.append({
                            "source": owner_id,
                            "called": called,
                            "file": file,
                            "line": line_no,
                            "language": language,
                        })

            self._index_javascript_references(
                file, masked, function_ranges
            )

        if language == "javascript":
            api_patterns = (
                re.compile(r"""\baxios\.(get|post|put|patch|delete)\s*\(\s*['"]([^'"]+)['"]""", re.I),
                re.compile(r"""\bfetch\s*\(\s*['"]([^'"]+)['"]\s*,\s*\{[^}]*?method\s*:\s*['"](GET|POST|PUT|PATCH|DELETE)['"]""", re.I | re.S),
            )
            for pattern_index, pattern in enumerate(api_patterns):
                for match in pattern.finditer(text):
                    if pattern_index == 0:
                        method, route = match.groups()
                    else:
                        route, method = match.groups()
                    line = self._line_number(text, match.start())
                    owner_id = next(
                        (node_id for start, end, node_id in function_ranges
                         if start <= line <= end),
                        None,
                    )
                    reference_id = self._add_node(
                        file, line, "api_reference",
                        f"{method.upper()} {route}",
                        lines[line - 1] if line <= len(lines) else "",
                        ["frontend", "api"],
                    )
                    if owner_id:
                        self._add_edge(
                            owner_id, reference_id, "references",
                            "api_call_owner",
                            f"{file}:{line} issues {method.upper()} {route}",
                        )

        for match in API_PATH.finditer(text):
            route = match.group(1)
            line = self._line_number(text, match.start())
            context = text[
                max(0, match.start() - 200):
                min(len(text), match.end() + 100)
            ]
            method_match = API_METHOD.search(context)
            method = method_match.group(1).upper() if method_match else None
            name = f"{method} {route}" if method else route
            excerpt = lines[line - 1] if line <= len(lines) else ""

            self._add_node(
                file, line, "api_reference", name,
                excerpt, ["frontend", "api"],
            )

        if language == "sql":
            self._index_sql(file, text)

    def _index_javascript_references(
        self,
        file: str,
        masked: str,
        function_ranges: list[tuple[int, int, str]],
    ) -> None:
        lines = masked.splitlines()

        for line_no, line in enumerate(lines, start=1):
            owner_id = next(
                (
                    node_id
                    for start, end, node_id in function_ranges
                    if start <= line_no <= end
                ),
                None,
            )

            for match in IDENTIFIER.finditer(line):
                name = match.group(0)
                if name in JS_KEYWORDS:
                    continue

                self._add_reference(
                    file, line_no, name, line, owner_id,
                    "javascript_lexical_identifier",
                )

    def _index_sql(self, file: str, text: str) -> None:
        clean = self._mask_sql(text)
        lines = text.splitlines()
        definition_matches = list(SQL_DEFINITION.finditer(clean))

        definitions = {
            match.group(1).lower()
            for match in definition_matches
        }
        definition_spans = [match.span() for match in definition_matches]

        for match in definition_matches:
            obj = match.group(1)
            line = self._line_number(text, match.start())
            excerpt = lines[line - 1] if line <= len(lines) else ""

            self._add_node(
                file, line, "database_object_definition",
                obj, excerpt, ["database"],
            )

        for match in SQL_OBJECT.finditer(clean):
            if any(start <= match.start() < end for start, end in definition_spans):
                continue
            obj = match.group(1)
            if obj.lower() in definitions:
                continue

            line = self._line_number(text, match.start())
            excerpt = lines[line - 1] if line <= len(lines) else ""

            self._add_node(
                file, line, "database_object_reference",
                obj, excerpt, ["database"],
            )

    def _module_candidates(self, importer: str, module: str) -> list[str]:
        base = Path(importer).parent
        is_relative = module.startswith(".")

        if is_relative:
            dots = len(module) - len(module.lstrip("."))
            remainder = module[dots:].replace(".", "/")
            parent = base
            for _ in range(max(0, dots - 1)):
                parent = parent.parent
            target = parent / remainder
        else:
            target = Path(module.replace(".", "/"))

        target = Path(str(target).replace("\\", "/"))
        possibilities = [target.as_posix()]

        if not target.suffix:
            for suffix in (".py", ".js", ".jsx", ".ts", ".tsx", ".vue"):
                possibilities.append(target.as_posix() + suffix)

            for suffix in (".js", ".jsx", ".ts", ".tsx", ".vue", ".py"):
                possibilities.append(
                    (target / ("index" + suffix)).as_posix()
                )

            possibilities.append((target / "__init__.py").as_posix())

        candidates = []
        for possibility in possibilities:
            normalized = Path(possibility)

            if is_relative:
                resolved = (self.root / normalized).resolve()
                try:
                    possibility = resolved.relative_to(
                        self.root
                    ).as_posix()
                except ValueError:
                    continue

            if (
                possibility in self.file_text
                and possibility not in candidates
            ):
                candidates.append(possibility)

        if not candidates and not is_relative:
            expected = target.as_posix().strip("/")
            suffixes = [expected + ext for ext in (".py", ".js", ".jsx", ".ts", ".tsx", ".vue")]
            suffixes.extend(
                (Path(expected) / ("index" + ext)).as_posix()
                for ext in (".py", ".js", ".jsx", ".ts", ".tsx", ".vue")
            )
            matches = sorted({
                candidate for candidate in self.file_text
                if any(candidate.endswith("/" + suffix) for suffix in suffixes)
                or candidate in suffixes
            })
            # A suffix match is safe only when the repository contains one candidate.
            if len(matches) == 1:
                candidates.append(matches[0])

        return candidates

    def _resolve_imports(self) -> None:
        for file, imports in self.file_imports.items():
            source_file_node = self.file_nodes.get(file)

            for item in imports:
                module = item["module"]
                bindings = item["bindings"]

                for target_file in self._module_candidates(file, module):
                    self._add_edge(
                        source_file_node,
                        self.file_nodes.get(target_file),
                        "imports",
                        "resolved_path",
                        f"{file}:{item['line']} imports {module}",
                    )

                    for local_name, imported_name in bindings.items():
                        self.imported_symbols[file][local_name].add(target_file)
                        self.imported_symbol_names[file][local_name] = imported_name.split(".")[-1]

                        target_symbols = [
                            node_id for (symbol_language, symbol_name), node_ids
                            in self.symbols.items()
                            if symbol_name == imported_name.split(".")[-1]
                            for node_id in node_ids
                            if self.nodes[node_id].file == target_file
                        ]
                        source_references = [
                            (reference_id, owner_id)
                            for reference_id, owner_id in self.reference_parent.items()
                            if self.nodes[reference_id].file == file
                            and self.nodes[reference_id].name == local_name
                        ]
                        for reference_id, owner_id in source_references:
                            for target_id in target_symbols:
                                self._add_edge(
                                    owner_id, target_id, "imports",
                                    "imported_symbol_reference",
                                    f"{file}:{self.nodes[reference_id].line} uses imported {local_name} from {target_file}",
                                )

    def _resolve_calls(self) -> None:
        for call in self.pending_calls:
            source_id = call["source"]
            called = call["called"]
            source_file = call["file"]
            language = call["language"]

            terminal = called.split(".")[-1]
            imported_name = self.imported_symbol_names[source_file].get(
                terminal, terminal
            )
            candidates = self.symbols.get((language, imported_name), [])

            allowed_files = {source_file}
            imported = self.imported_symbols[source_file]

            if "." in called:
                allowed_files.update(
                    imported.get(called.split(".")[0], set())
                )
            else:
                allowed_files.update(imported.get(terminal, set()))

            resolved = [
                item for item in candidates
                if self.nodes[item].file in allowed_files
            ]

            for target_id in resolved:
                target_file = self.nodes[target_id].file
                confidence = (
                    "same_file_symbol"
                    if target_file == source_file
                    else "imported_symbol"
                )

                self._add_edge(
                    source_id,
                    target_id,
                    "calls",
                    confidence,
                    f"{source_file}:{call['line']} calls {called}",
                )

    def _resolve_api_routes(self) -> None:
        references = [
            node for node in self.nodes.values()
            if node.kind == "api_reference"
        ]
        endpoints = [
            node for node in self.nodes.values()
            if node.kind == "api_endpoint"
        ]

        for reference in references:
            parts = reference.name.split(" ", 1)
            if len(parts) != 2:
                continue

            method, route = parts
            for endpoint in endpoints:
                if endpoint.file == reference.file:
                    continue

                endpoint_parts = endpoint.name.split(" ", 1)
                if len(endpoint_parts) != 2:
                    continue

                endpoint_method, endpoint_route = endpoint_parts

                if (
                    method == endpoint_method
                    and self._normalize_route(route)
                    == self._normalize_route(endpoint_route)
                ):
                    self._add_edge(
                        reference.id,
                        endpoint.id,
                        "api",
                        "exact_method_and_path",
                        f"{method} {route}",
                    )

    @staticmethod
    def _normalize_route(route: str) -> str:
        route = re.sub(r"\{[^{}]+\}", "{}", route.strip())
        route = re.sub(r"/+", "/", route)
        return route.rstrip("/") or "/"

    def _resolve_model_keys(
        self,
        source_file: str,
        local_name: str,
        owner_id: str | None = None,
    ) -> list[tuple[str, str]]:
        """Resolve a local symbol or function-scoped alias to indexed models."""
        names = [local_name]
        if owner_id:
            alias_target = self.model_aliases.get((source_file, owner_id, local_name))
            if alias_target and alias_target not in names:
                names.append(alias_target)

        resolved = set()
        for name in names:
            local_key = (source_file, name)
            if local_key in self.model_tables:
                resolved.add(local_key)

            imported_name = self.imported_symbol_names[source_file].get(name, name)
            for target_file in self.imported_symbols[source_file].get(name, set()):
                imported_key = (target_file, imported_name)
                if imported_key in self.model_tables:
                    resolved.add(imported_key)

        return sorted(resolved)

    def _resolve_semantic_model_references(self) -> None:
        """Connect model and model-column references only when symbols resolve."""
        for item in self.pending_model_aliases:
            self.model_aliases[(item["file"], item["owner"], item["alias"])] = item["model"]

        for item in self.pending_model_references:
            source_file = item["file"]
            local_name = item["name"]
            member = item.get("member")
            resolved_models = self._resolve_model_keys(
                source_file, local_name, item.get("source")
            )

            for model_key in resolved_models:
                if member:
                    target_id = self.model_column_nodes.get(
                        (model_key[0], model_key[1], member)
                    )
                    if target_id:
                        self._add_edge(
                            item["source"], target_id, "references",
                            "resolved_ast_model_column",
                            f"{source_file}:{item['line']} resolves "
                            f"{local_name}.{member} to "
                            f"{self.model_tables[model_key]}.{member}: "
                            f"{item['evidence']}",
                            graph="semantic",
                        )
                else:
                    target_id = self.model_class_nodes.get(model_key)
                    if target_id:
                        self._add_edge(
                            item["source"], target_id, "references",
                            "resolved_ast_model_symbol",
                            f"{source_file}:{item['line']} uses resolved model "
                            f"{local_name}: {item['evidence']}",
                            graph="semantic",
                        )

    def _resolve_sql_objects(self) -> None:
        """Resolve ORM model references and foreign-key targets conservatively."""
        definitions = defaultdict(list)
        columns = defaultdict(list)

        for node in self.nodes.values():
            if node.kind == "database_object_definition":
                definitions[node.name.lower()].append(node)
            elif node.kind == "database_column_definition":
                columns[node.name.lower()].append(node)

        # Resolve explicit SQL object references.
        for node in list(self.nodes.values()):
            if node.kind != "database_object_reference":
                continue
            for definition in definitions.get(node.name.lower(), []):
                self._add_edge(
                    node.id, definition.id, "sql", "exact_object_name",
                    f"SQL object reference: {node.name}",
                )

        # Only create ORM references when the identifier resolves to a known
        # SQLAlchemy model in the same file or through an explicit import.
        for item in self.pending_orm_references:
            source_file = item["file"]
            model_name = item["name"]
            resolved_models = self._resolve_model_keys(
                source_file, model_name, item.get("source")
            )

            for model_key in resolved_models:
                model_file, resolved_name = model_key
                reference_id = self._add_node(
                    source_file, item["line"], "database_object_reference",
                    resolved_name,
                    f"{item['call']}({model_name})",
                    ["database", "backend"],
                )
                self._add_edge(
                    item["source"], reference_id, "sql", "orm_model_argument",
                    f"{source_file}:{item['call_line']} uses resolved model {model_name} in {item['call']}",
                )
                table_id = self.model_table_nodes.get(model_key)
                self._add_edge(
                    reference_id, table_id, "sql", "orm_model_to_table",
                    f"{resolved_name} maps to {self.model_tables[model_key]}",
                )

        # Resolve ForeignKey("table.column") to a concrete column when possible.
        table_by_name = defaultdict(list)
        for model_key, table_name in self.model_tables.items():
            table_id = self.model_table_nodes.get(model_key)
            table_by_name[table_name.lower()].append((model_key, table_id))

        for item in self.pending_foreign_keys:
            if item.get("kind") == "composite":
                continue

            target = item["target"].replace('"', '').replace("'", "").strip()

            parts = [part for part in target.split(".") if part]
            if len(parts) < 2:
                continue
            target_table, target_column = parts[-2], parts[-1]
            matched = False
            for model_key, table_id in table_by_name.get(target_table.lower(), []):
                target_column_id = self.model_column_nodes.get(
                    (model_key[0], model_key[1], target_column)
                )
                if target_column_id:
                    self._add_edge(
                        item["source"], target_column_id, "sql",
                        "sqlalchemy_foreign_key",
                        f"{item['model']}.{item['column']} references {target}",
                    )
                    matched = True
                elif table_id:
                    self._add_edge(
                        item["source"], table_id, "sql",
                        "sqlalchemy_foreign_key_table",
                        f"{item['model']}.{item['column']} references {target}",
                    )
                    matched = True
            if not matched:
                unresolved_id = self._add_node(
                    item["file"], item["line"], "database_object_reference",
                    target_table,
                    f"ForeignKey({target!r})",
                    ["database", "backend"],
                )
                self._add_edge(
                    item["source"], unresolved_id, "sql",
                    "unresolved_foreign_key_target",
                    f"Declared foreign key target could not be indexed: {target}",
                )


        # Resolve composite ForeignKeyConstraint column pairs.
        for item in self.pending_foreign_keys:
            if item.get("kind") != "composite":
                continue

            source_file = item["file"]
            model_name = item["model"]

            for source_name, target in zip(
                item["source_columns"],
                item["target_columns"],
            ):
                source_id = self.model_column_nodes.get(
                    (source_file, model_name, source_name)
                )

                if not source_id:
                    continue

                target = target.strip().strip('"').strip("'")
                parts = [part for part in target.split(".") if part]

                if len(parts) < 2:
                    continue

                target_table = parts[-2]
                target_column = parts[-1]
                resolved = False

                for model_key, table_id in table_by_name.get(
                    target_table.lower(), []
                ):
                    target_column_id = self.model_column_nodes.get(
                        (model_key[0], model_key[1], target_column)
                    )

                    if target_column_id:
                        self._add_edge(
                            source_id,
                            target_column_id,
                            "sql",
                            "sqlalchemy_composite_foreign_key",
                            f"{model_name}.{source_name} references {target}",
                        )
                        resolved = True
                    elif table_id:
                        self._add_edge(
                            source_id,
                            table_id,
                            "sql",
                            "sqlalchemy_composite_foreign_key_table",
                            f"{model_name}.{source_name} references {target}",
                        )
                        resolved = True

                if not resolved:
                    target_id = self._add_node(
                        item["file"],
                        item["line"],
                        "database_object_reference",
                        target,
                        f"ForeignKeyConstraint target: {target}",
                        ["database", "backend"],
                    )

                    self._add_edge(
                        source_id,
                        target_id,
                        "sql",
                        "unresolved_composite_foreign_key",
                        f"Could not resolve composite FK target: {target}",
                    )

    def _build_index(self) -> None:
        for file, text in self.file_text.items():
            if file.endswith(".py"):
                self._index_python(file, text)
            else:
                self._index_text_source(file, text)

        for file in self.file_text:
            self.file_nodes[file] = self._add_node(
                file, 1, "source_file", file, "",
                self._tags_for(self.file_text[file][:3000], file),
            )

        for file, reference_id in self.reference_owners:
            self._add_edge(
                self.file_nodes[file],
                reference_id,
                "references",
                "file_level_reference",
                f"Top-level reference in {file}",
            )

        self._resolve_imports()
        self._resolve_calls()
        self._resolve_api_routes()
        self._resolve_semantic_model_references()
        self._resolve_sql_objects()

    @staticmethod
    def _topic_terms(topic: str) -> tuple[str, set[str]]:
        phrase = re.sub(r"\s+", " ", topic.lower()).strip()
        terms = {
            term.lower()
            for term in IDENTIFIER.findall(topic)
            if len(term) > 1
            and term.lower() not in COMMON_TOPIC_WORDS
        }
        return phrase, terms

    @staticmethod
    def _identifier_match(term: str, text: str) -> bool:
        return bool(re.search(
            rf"(?<![a-z0-9_$]){re.escape(term)}(?![a-z0-9_$])",
            text.lower(),
        ))

    @staticmethod
    def _scope_matches(file: str, scope: set[str]) -> bool:
        suffix = Path(file).suffix.lower()
        return any(
            suffix in SCOPE_EXTENSIONS[item]
            for item in scope
        )

    def _score_node(
        self,
        node: SourceNode,
        phrase: str,
        terms: set[str],
    ) -> dict | None:
        name = node.name.lower()
        file = node.file.lower()

        score = 0
        reasons = []
        matched = set()

        if phrase == name:
            score += 40
            reasons.append("exact_phrase_in_name")
        elif len(phrase) >= 4 and phrase in name:
            score += 20
            reasons.append("phrase_in_name")

        if phrase and phrase in file:
            score += 10
            reasons.append("phrase_in_path")

        for term in terms:
            if self._identifier_match(term, name):
                matched.add(term)

        if matched:
            score += len(matched) * 15
            reasons.append("identifier_match_in_name")
            if node.kind == "database_column_definition":
                score += 25
                reasons.append("database_column_definition")

        if not score:
            return None

        kind_weights = {
            "function": 8,
            "class": 8,
            "api_endpoint": 12,
            "api_reference": 12,
            "database_object_definition": 12,
            "database_column_definition": 18,
            "database_object_reference": 10,
            "component_usage": 5,
            "source_file": -8,
            "sql_statement": 10,
            "database_column_reference": 18,
        }
        score += kind_weights.get(node.kind, 0)

        return {
            "score": score,
            "node_id": node.id,
            "reasons": reasons,
            "matched_terms": sorted(matched),
        }

    def _find_reference_seeds(
        self,
        terms: set[str],
        selected_scope: set[str],
    ) -> list[dict]:
        matches = []

        for node in self.nodes.values():
            if node.kind != "identifier_reference":
                continue
            if not self._scope_matches(node.file, selected_scope):
                continue

            matched_terms = sorted({
                term for term in terms
                if self._identifier_match(term, node.name)
            })
            if not matched_terms:
                continue

            owner_id = (
                self.reference_parent.get(node.id)
                or self.file_nodes.get(node.file)
            )
            owner = self.nodes.get(owner_id) if owner_id else None

            if not owner or owner.kind == "source_file":
                continue

            matches.append({
                "score": 25 + len(matched_terms) * 5,
                "node_id": owner_id,
                "reference_id": node.id,
                "reasons": ["exact_identifier_reference"],
                "matched_terms": matched_terms,
            })

        return matches

    def _select_seeds(
        self,
        phrase: str,
        terms: set[str],
        selected_scope: set[str],
        max_nodes: int,
    ) -> tuple[list[dict], int]:
        candidates = []

        for node in self.nodes.values():
            if node.kind == "identifier_reference":
                continue
            if not self._scope_matches(node.file, selected_scope):
                continue

            match = self._score_node(node, phrase, terms)
            if match:
                candidates.append(match)

        candidates.extend(
            self._find_reference_seeds(terms, selected_scope)
        )

        best_by_node = {}
        for item in candidates:
            node_id = item["node_id"]
            previous = best_by_node.get(node_id)
            if previous is None or item["score"] > previous["score"]:
                best_by_node[node_id] = item
            elif previous and item.get("reference_id"):
                previous.setdefault("evidence", []).append(item["reference_id"])

        candidates = list(best_by_node.values())

        def seed_priority(item: dict) -> tuple:
            node = self.nodes[item["node_id"]]
            tags = set(node.tags)
            semantic_priority = 0

            if node.kind in {
                    "database_column_definition",
                    "database_column_reference",
                }:
                    semantic_priority += 30
            elif node.kind in {"api_reference", "api_endpoint"}:
                semantic_priority += 25
            elif node.kind in {"function", "class"}:
                semantic_priority += 10

            semantic_priority += 5 if "frontend" in tags else 0
            semantic_priority += 4 if "api" in tags else 0
            semantic_priority += 3 if "authentication" in tags else 0
            semantic_priority += 2 if "ownership" in tags else 0

            if node.kind == "source_file":
                semantic_priority -= 100

            return (-item["score"], -semantic_priority, item["node_id"])

        candidates.sort(key=seed_priority)
        self.match_candidates = candidates

        matched_count = len(candidates)

        # Keep a broad but bounded seed set. The previous eight-seed cap
        # discarded equally relevant frontend and backend entry points.
        seed_limit = min(
            matched_count,
            max_nodes,
            max(12, min(32, max_nodes // 5 or 1)),
        )

        return candidates[:seed_limit], matched_count

    def trace(
        self,
        topic: str,
        max_nodes: int = 160,
        scope: Iterable[str] | None = None,
        relations: Iterable[str] | None = None,
        depth: int = 3,
    ) -> dict:
        if not topic or not topic.strip():
            raise ValueError("Topic must not be empty.")
        if max_nodes < 1:
            raise ValueError("max_nodes must be greater than zero.")
        if depth < 1 or depth > 20:
            raise ValueError("Depth must be between 1 and 20.")

        selected_scope = set(VALID_SCOPES if scope is None else scope)
        selected_relations = set(
            VALID_RELATIONS if relations is None else relations
        )

        if not selected_scope:
            raise ValueError("At least one scope must be selected.")
        if not selected_relations:
            raise ValueError("At least one relationship must be selected.")

        invalid_scope = selected_scope - VALID_SCOPES
        invalid_relations = selected_relations - VALID_RELATIONS

        if invalid_scope:
            raise ValueError(
                f"Unsupported scope values: {sorted(invalid_scope)}"
            )
        if invalid_relations:
            raise ValueError(
                f"Unsupported relationship values: {sorted(invalid_relations)}"
            )

        self._reset()
        self._read_sources()
        self._build_index()

        phrase, terms = self._topic_terms(topic)
        seed_items, matched_count = self._select_seeds(
            phrase, terms, selected_scope, max_nodes
        )

        seed_ids = {item["node_id"] for item in seed_items}

        # Identifier references remain indexed as evidence, but are not
        # traversed as ordinary graph nodes. This prevents lexical noise
        # from consuming the trace node budget.
        adjacency = defaultdict(set)
        for edge in self.edges:
            if edge.relation not in selected_relations:
                continue

            source = self.nodes.get(edge.source)
            target = self.nodes.get(edge.target)
            if (
                not source
                or not target
                or source.kind == "identifier_reference"
                or target.kind == "identifier_reference"
            ):
                continue

            # Preserve the original directed edge in the graph, while
            # allowing traversal from both dependencies and dependents.
            adjacency[edge.source].add(edge.target)
            adjacency[edge.target].add(edge.source)

        for source in adjacency:
            adjacency[source] = sorted(adjacency[source])

        selected = set(seed_ids)
        node_depth = {seed_id: 0 for seed_id in seed_ids}
        queue = deque((seed_id, 0) for seed_id in sorted(seed_ids))
        truncated = False

        while queue:
            current, current_depth = queue.popleft()

            if current_depth >= depth:
                continue

            for neighbor in adjacency.get(current, []):
                if neighbor in selected:
                    continue

                target_node = self.nodes.get(neighbor)
                if not target_node:
                    continue
                if not self._scope_matches(target_node.file, selected_scope):
                    continue

                if len(selected) >= max_nodes:
                    truncated = True
                    break

                selected.add(neighbor)
                node_depth[neighbor] = current_depth + 1
                queue.append((neighbor, current_depth + 1))

            if truncated:
                break

        result_nodes = []
        for node_id in selected:
            node = self.nodes[node_id]
            item = asdict(node)
            item["depth"] = node_depth[node_id]
            result_nodes.append(item)

        result_nodes.sort(
            key=lambda item: (
                item["file"], item["line"], item["kind"], item["name"]
            )
        )

        result_edges = [
            asdict(edge)
            for edge in self.edges
            if (
                edge.source in selected
                and edge.target in selected
                and edge.relation in selected_relations
                and self.nodes[edge.target].kind != "identifier_reference"
            )
        ]
        result_edges.sort(
            key=lambda item: (
                item["source"], item["relation"], item["target"]
            )
        )

        files = sorted({
            node["file"]
            for node in result_nodes
            if node["kind"] != "source_file"
        })

        match_reasons = {
            item["node_id"]: {
                "score": item["score"],
                "reasons": item["reasons"],
                "matched_terms": item["matched_terms"],
                "evidence_references": item.get("evidence", [])
                + ([item["reference_id"]] if item.get("reference_id") else []),
            }
            for item in seed_items
        }

        trace_categories = defaultdict(list)
        kind_counts = defaultdict(int)
        depth_counts = defaultdict(int)

        for node in result_nodes:
            kind_counts[node["kind"]] += 1
            depth_counts[node["depth"]] += 1
            for tag in node["tags"]:
                trace_categories[tag].append(node["id"])

        result = {
            "version": "6.8",
            "topic": topic,
            "repository": str(self.root),
            "options": {
                "scope": sorted(selected_scope),
                "relations": sorted(selected_relations),
                "depth": depth,
                "max_nodes": max_nodes,
                "traversal_mode": "bidirectional",
                "graph_types": ["structural", "semantic"],
            },
            "summary": {
                "files_scanned": len(self.file_text),
                "indexed_nodes": len(self.nodes),
                "matched_nodes": matched_count,
                "selected_seeds": len(seed_ids),
                "trace_nodes": len(result_nodes),
                "trace_edges": len(result_edges),
                "graph_edges": {
                    "structural": sum(
                        edge.graph == "structural" for edge in self.edges
                        if edge.source in selected and edge.target in selected
                        and edge.relation in selected_relations
                    ),
                    "semantic": sum(
                        edge.graph == "semantic" for edge in self.edges
                        if edge.source in selected and edge.target in selected
                        and edge.relation in selected_relations
                    ),
                },
                "files_in_trace": len(files),
                "node_kinds": dict(sorted(kind_counts.items())),
                "nodes_by_depth": dict(sorted(depth_counts.items())),
                "max_nodes_reached": len(selected) >= max_nodes,
                "traversal_truncated": truncated,
            },
            "seeds": [
                {
                    "node_id": item["node_id"],
                    "score": item["score"],
                    "reasons": item["reasons"],
                    "matched_terms": item["matched_terms"],
                    "evidence_references": item.get("evidence", [])
                    + ([item["reference_id"]] if item.get("reference_id") else []),
                }
                for item in seed_items
            ],
            "match_reasons": match_reasons,
            "matched_candidates": [
                {
                    "node_id": item["node_id"],
                    "score": item["score"],
                    "reasons": item["reasons"],
                    "matched_terms": item["matched_terms"],
                    "reference_id": item.get("reference_id"),
                    "evidence_references": item.get("evidence", [])
                    + ([item["reference_id"]] if item.get("reference_id") else []),
                    "selected_as_seed": item["node_id"] in seed_ids,
                }
                for item in getattr(self, "match_candidates", [])
            ],
            "deferred_seeds": [
                {
                    "node_id": item["node_id"],
                    "score": item["score"],
                    "reason": "seed_limit",
                }
                for item in getattr(self, "match_candidates", [])
                if item["node_id"] not in seed_ids
            ],
            "trace_categories": dict(trace_categories),
            "layer_categories": dict(trace_categories),
            "files": files,
            "nodes": result_nodes,
            "edges": result_edges,
            "limitations": [
                "Static analysis identifies source relationships; it does not prove runtime execution.",
                "Python analysis uses AST; JavaScript, TypeScript, and Vue analysis uses lightweight lexical scanning.",
                "API matching supports common axios calls and FastAPI route declarations; dynamic wrappers and prefixes may remain unresolved.",
                "Database analysis supports SQL references, common SQLAlchemy mappings, and statically declared foreign keys.",
                "Semantic ORM links require a locally defined or explicitly imported model; dynamic mappings may remain unresolved.",
                "Call resolution is limited to same-file symbols and resolved imports; reflection and runtime dispatch are not resolved.",
                "Traversal is bidirectional, while each reported edge retains its original direction and evidence.",
                "No repository source file is modified by this tool.",
            ],
        }

        result["plain_language_summary"] = (
            build_plain_language_summary(result)
        )

        return result 

def build_plain_language_summary(result: dict) -> dict:
    """Build an evidence-based Persian summary of a trace report."""

    stats = result["summary"]
    nodes = result["nodes"]
    edges = result["edges"]

    def names_for(*kinds: str, limit: int = 5) -> list[str]:
        values = []
        for node in nodes:
            if node["kind"] in kinds and node["name"] not in values:
                values.append(node["name"])
        return values[:limit]

    def display_names(values: list[str]) -> str:
        return "، ".join(values)

    lines = [
        f"موضوع بررسی «{result['topic']}» بوده است. "
        f"ابزار {stats['files_scanned']} فایل را بررسی کرده و "
        f"{stats['matched_nodes']} مورد مرتبط پیدا کرده است."
    ]

    if not stats["selected_seeds"]:
        lines.append(
            "هیچ نقطه شروع مناسبی برای ردیابی پیدا نشد."
        )
    else:
        lines.append(
            f"{stats['selected_seeds']} نقطه شروع انتخاب شده و "
            f"{stats['trace_nodes']} عنصر با "
            f"{stats['trace_edges']} ارتباط در گزارش ثبت شده است."
        )

    findings = []

    api_nodes = names_for("api_endpoint", "api_reference")
    functions = names_for("function")
    sql_nodes = names_for("sql_statement")
    tables = names_for(
        "database_object_reference",
        "database_object_definition",
    )
    columns = names_for(
        "database_column_reference",
        "database_column_definition",
        limit=8,
    )

    if api_nodes:
        findings.append("APIها: " + display_names(api_nodes))
    if functions:
        findings.append("توابع: " + display_names(functions))
    if sql_nodes:
        findings.append(f"{len(sql_nodes)} دستور SQL")
    if tables:
        findings.append("اشیای پایگاه داده: " + display_names(tables))
    if columns:
        findings.append("نمونه ستون‌ها: " + display_names(columns))

    if findings:
        lines.append(
            "اجزای مهم شناسایی‌شده: " + "؛ ".join(findings) + "."
        )

    if edges:
        relation_counts = {}
        for edge in edges:
            relation_counts[edge["relation"]] = (
                relation_counts.get(edge["relation"], 0) + 1
            )

        relation_text = "، ".join(
            f"{count} ارتباط از نوع {relation}"
            for relation, count in sorted(relation_counts.items())
        )
        lines.append("ارتباطات استخراج‌شده: " + relation_text + ".")
    else:
        lines.append("ارتباط مستقیمی بین عناصر گزارش‌شده ثبت نشده است.")

    if stats["traversal_truncated"] or stats["max_nodes_reached"]:
        lines.append(
            "محدودیت تعداد عناصر یا عمق ردیابی فعال شده است؛ "
            "ممکن است تمام ارتباطات در گزارش دیده نشوند."
        )

    lines.append(
        "این گزارش حاصل تحلیل ایستای سورس‌کد است و اجرای واقعی "
        "مسیرهای شناسایی‌شده را اثبات نمی‌کند."
    )

    return {
        "language": "fa",
        "title": "خلاصه قابل فهم گزارش",
        "text": "\n".join(lines),
    }
       
def trace_source_topic(
    repository: str | Path,
    topic: str,
    max_nodes: int = 160,
    scope: Iterable[str] | None = None,
    relations: Iterable[str] | None = None,
    depth: int = 3,
) -> dict:
    """Public entry point for repository-wide source topic tracing."""
    return TopicTracer(repository).trace(
        topic=topic,
        max_nodes=max_nodes,
        scope=scope,
        relations=relations,
        depth=depth,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trace a topic across a source repository."
    )

    parser.add_argument("repository", help="Repository root directory")
    parser.add_argument("topic", help="Topic, symbol, field, API, or workflow")
    parser.add_argument("--max-nodes", type=int, default=160)
    parser.add_argument("--depth", type=int, default=3)

    parser.add_argument(
        "--scope",
        nargs="+",
        choices=sorted(VALID_SCOPES),
        default=sorted(VALID_SCOPES),
    )
    parser.add_argument(
        "--relations",
        nargs="+",
        choices=sorted(VALID_RELATIONS),
        default=sorted(VALID_RELATIONS),
    )

    parser.add_argument("--json", action="store_true")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--edges", action="store_true")
    parser.add_argument("--details", action="store_true")

    args = parser.parse_args()

    try:
        result = trace_source_topic(
            repository=args.repository,
            topic=args.topic,
            max_nodes=args.max_nodes,
            scope=args.scope,
            relations=args.relations,
            depth=args.depth,
        )
    except (ValueError, NotADirectoryError) as exc:
        parser.error(str(exc))
        return

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"\nTOPIC: {result['topic']}")
    for key, value in result["summary"].items():
        print(f"{key.upper().replace('_', ' ')}: {value}")

    if args.summary:
        print("\n" + result["plain_language_summary"]["title"])
        print("-" * 60)
        print(result["plain_language_summary"]["text"])
        return

    print("\nTRACE FILES:")
    for file in result["files"]:
        print(f"  {file}")

    print("\nSEEDS:")
    for seed in result["seeds"]:
        print(
            f"  {seed['node_id']} | score={seed['score']} | "
            f"{', '.join(seed['reasons'])}"
        )

    if args.edges:
        print("\nRELATIONSHIPS:")
        for edge in result["edges"]:
            evidence = re.sub(r"\s+", " ", edge["evidence"]).strip()
            if len(evidence) > 180:
                evidence = evidence[:177] + "..."
            print(
                f"  {edge['source']} --{edge['relation']}--> "
                f"{edge['target']} [{edge['graph']}|{edge['confidence']}]"
            )
            if evidence:
                print(f"    evidence: {evidence}")

    if args.details:
        print("\nTRACE NODES:")
        for node in result["nodes"]:
            print(
                f"  [depth={node['depth']}] [{node['kind']}] "
                f"{node['file']}:{node['line']} — {node['name']}"
            )

        print("\nLIMITATIONS:")
        for item in result["limitations"]:
            print(f"  - {item}")
    else:
        print("\nNOTE: Static relationships are evidence-based candidates, not proof of runtime execution.")

    print("\n" + result["plain_language_summary"]["title"])
    print("-" * 60)
    print(result["plain_language_summary"]["text"])

if __name__ == "__main__":
    main()