---
name: modern-python
description: Write Python that uses the newest language and stdlib features the project's minimum Python version allows, and nothing newer. Use whenever writing, editing, refactoring, reviewing or generating Python (.py files, scripts, tests, notebooks), even if the user never mentions versions. Reads the target from requires-python and other version pins, then applies idioms such as `X | None`, `def f[T]`, `copy.replace` and lazy imports, and avoids removed APIs. Covers Python 3.11 through 3.15.
---

# Modern Python for the project's version

Training data skews old: `typing.List`, `Optional[...]`, `TypeVar` boilerplate, quoted forward refs, `datetime.utcnow()`, `asyncio.get_event_loop()`. Some is dated, some no longer runs. Old code in the file amplifies it: you copy it. Opposite failure: `def f[T]` in a library supporting 3.11 breaks its users.

**Rule: clearest idiom available at the project's minimum supported version.**

## Step 1: Target version (once per project/session)

Search project root (walk up from working file):

| Source | Where | Kind |
|---|---|---|
| `pyproject.toml` | `[project] requires-python`, `[tool.poetry.dependencies] python` | declared range |
| `setup.cfg` / `setup.py` | `python_requires` | declared range |
| `.python-version`, `.tool-versions`, `runtime.txt` | interpreter pin | pinned |
| `Dockerfile*` | `FROM python:X.Y…` | pinned |
| `pyproject.toml` | `[tool.ruff] target-version`, `[tool.mypy] python_version`, `[tool.pyright] pythonVersion`, `[tool.black] target-version` | tooling |
| CI (`.github/workflows/*.yml`, `tox.ini`, `noxfile.py`) | lowest matrix version | tooling |

First rule that applies:

1. User names version → use it.
2. Lowest of declared range floor, tooling targets, CI floor. `requires-python = ">=3.11"` + `.python-version` 3.14 → 3.11; the pin is only the dev interpreter.
3. None of those → lowest pinned interpreter.
4. Nothing → throwaway script: interpreter that runs it. Shared code: state assumption in one line.

| Specifier | Target |
|---|---|
| `>=3.12,<4` | 3.12 |
| `~=3.13.2` | 3.13 |
| `==3.14.*` | 3.14 |
| `^3.11` (Poetry) | 3.11 |
| `>3.11` | 3.11 (3.11.1 satisfies it) |

Floor < 3.11: out of scope. Write conservatively for it; suggest raising floor (3.10 and older at/past EOL).

Report a tooling target above the floor: ruff `py313` under `>=3.11` passes syntax that breaks on 3.11.

## Step 2: Features at or below target

Use rows and sections at or below target; higher ones forbidden. Swaps live only in the quick table; version sections hold the rest.

### Quick table

| Old | New | Min |
|---|---|---|
| `asyncio.get_event_loop()` at program entry, no running loop (raises from 3.14) | `asyncio.run()` | 3.7 |
| `asyncio.get_event_loop()` in coroutine or callback | `asyncio.get_running_loop()` | 3.7 |
| `List[int]`, `Dict[str, X]`, `Tuple`, `Type` | `list[int]`, `dict[str, X]`, `tuple`, `type` | 3.9 |
| `s[len(p):] if s.startswith(p)` | `s.removeprefix(p)` / `removesuffix` | 3.9 |
| `Optional[X]`, `Union[A, B]` | `X \| None`, `A \| B` | 3.10 |
| long `if/elif` on data shape/type | `match`/`case` (only if clearer) | 3.10 |
| `zip(a, b)`, lengths must match | `zip(a, b, strict=True)` | 3.10 |
| `toml`/`tomli` for reading | `tomllib` | 3.11 |
| `asyncio.gather` + manual cancel, `wait_for` | `asyncio.TaskGroup`, `asyncio.timeout()` | 3.11 |
| `T = TypeVar("T", bound="Foo")` to return self | `typing.Self` | 3.11 |
| `datetime.utcnow()` | `datetime.now(UTC)` (`from datetime import UTC`) | 3.11 |
| `T = TypeVar("T")` + `Generic[T]` | `def f[T](...)`, `class C[T]:` | 3.12 |
| `X: TypeAlias = ...` | `type X = ...` | 3.12 |
| `zip(*[iter(it)] * n)` chunking | `itertools.batched(it, n)` | 3.12 |
| nothing | `@override` on overriding methods | 3.12 |
| `dataclasses.replace` / `nt._replace` in generic code | `copy.replace(obj, **changes)` (any `__replace__`) | 3.13 |
| `warnings.warn` only | `@warnings.deprecated("...")` | 3.13 |
| `TypeGuard[X]` | `TypeIs[X]` when X is a subtype of the input type; else keep `TypeGuard` | 3.13 |
| sentinel to stop queue consumer | `Queue.shutdown()` + `except ShutDown` (`QueueShutDown` in asyncio) | 3.13 |
| `os.cpu_count()` for pool sizing | `os.process_cpu_count()` | 3.13 |
| `"Foo"` quoted forward refs, `from __future__ import annotations` | bare `Foo` | 3.14 |
| `except (A, B):` without `as` | `except A, B:` (optional) | 3.14 |
| `uuid4()` for sortable DB keys | `uuid.uuid7()` | 3.14 |
| `shutil.copytree(src, dst)` on Paths | `src.copy(dst)` / `src.move(dst)` | 3.14 |
| string-built SQL/HTML/shell | t-string `t"..."` + processor | 3.14 |
| `_MISSING = object()` | `MISSING = sentinel("MISSING")` | 3.15 |
| `MappingProxyType(dict(...))` constants, hashable-dict hacks | `frozendict(...)` | 3.15 |
| `[x for L in lists for x in L]`, `chain.from_iterable` | `[*L for L in lists]` | 3.15 |
| `import heavy` inside functions for startup | `lazy import heavy` at module top | 3.15 |
| `re.match` (soft-deprecated) | `re.prefixmatch` | 3.15 |

### ≤3.10 (always available)
Walrus, `functools.cache`, `zoneinfo` (not `pytz`), `importlib.metadata` (not `pkg_resources`), `@dataclass(slots=True, kw_only=True)`, `itertools.pairwise`, `ParamSpec`. Already removed, old code still uses: `collections.Mapping` etc. (→ `collections.abc`), `loop=` on asyncio high-level APIs.

### 3.11
- **Language:** `ExceptionGroup`, `except*`, `exc.add_note()`.
- **Typing:** `LiteralString`, `Required`/`NotRequired`, `TypeVarTuple`/`Unpack`, `assert_never`, `reveal_type`, `dataclass_transform`, generic `TypedDict`/`NamedTuple`.
- **Stdlib:** `asyncio.Runner`; `enum.StrEnum`, `verify`, `member`/`nonmember`; `contextlib.chdir`, `operator.call`, `hashlib.file_digest`, `math.cbrt/exp2`; `re` atomic groups `(?>...)`, possessive `*+`.
- **Removed:** `@asyncio.coroutine` (→ `async def`), `binhex`, `inspect.getargspec/formatargspec` (→ `inspect.signature`).

### 3.12
- **Language:** PEP 695 bounds `[T: Hashable]`, constraints `[T: (int, str)]`, `[*Ts]`, `[**P]`; `type` aliases are lazy and may be generic. f-strings: reuse outer quotes, backslashes, multiline with comments. Invalid escapes (`"\d"`) warn → raw strings.
- **Typing:** `**kwargs: Unpack[SomeTypedDict]`; `collections.abc.Buffer` not `ByteString`. `typing.Hashable`/`Sized` deprecated → `collections.abc`.
- **Stdlib:** `math.sumprod`, `Path.walk()`, subclassable `Path`, `relative_to(walk_up=True)`, `glob(case_sensitive=)`, `os.path.splitroot()`, `asyncio.eager_task_factory`, `asyncio.run(loop_factory=)`, `shutil.rmtree(onexc=)`, `NamedTemporaryFile(delete_on_close=)`, `sqlite3.connect(autocommit=)`, `calendar.Month/Day`, `sys.monitoring`; `tarfile` `extractall(filter="data")`. `datetime.utcnow()/utcfromtimestamp()` deprecated.
- **Removed:** `distutils` (→ setuptools/sysconfig/packaging), `imp` (→ importlib), `asyncore`/`asynchat` (→ asyncio), `smtpd`, unittest aliases (`assertEquals`, `failUnless`, `assertRegexpMatches`…), `SafeConfigParser`/`readfp`, `ssl.wrap_socket` (→ `SSLContext.wrap_socket`), `ssl.match_hostname`, `locale.format`. venv no longer installs setuptools.

### 3.13
- **Typing:** type-param defaults `class Box[T = int]`; `ReadOnly` TypedDict items; `get_protocol_members()`, `is_protocol()`. `typing.AnyStr` deprecated → `def f[S: (str, bytes)](x: S) -> S`.
- **Stdlib:** `itertools.batched(strict=True)`; `math.fma()`; `statistics.kde()`; `base64.z85encode/decode`; `Path.from_uri()`, `PurePath.full_match()`, `glob.translate()`; `argparse add_argument(deprecated=True)`; `re.PatternError`; `mimetypes.guess_file_type()`; `dbm.sqlite3`.
- **Removed:** `aifc audioop cgi cgitb chunk crypt imghdr mailcap msilib nis nntplib ossaudiodev pipes sndhdr spwd sunau telnetlib uu xdrlib`, `lib2to3`, `tkinter.tix`, `locale.resetlocale`, `typing.io/re`, chained `classmethod` descriptors, `unittest.makeSuite`. Replacements: `cgi.parse_header` → `email.message.EmailMessage`; `pipes.quote` → `shlex.quote`; `crypt` → `hashlib`/`bcrypt`; `imghdr` → `filetype`; `telnetlib` → `telnetlib3`; `uu` → `base64`.
- **Behavior:** `locals()` in functions returns snapshots → pass explicit namespaces to `exec`/`eval`. `ssl.create_default_context()` stricter (`VERIFY_X509_STRICT`).

### 3.14
- **Language:** lazy annotations (PEP 649/749); introspect via `annotationlib.get_annotations(obj, format=Format.FORWARDREF)`, not class `__annotations__`. `t"..."` → `string.templatelib.Template`. `return`/`break`/`continue` leaving `finally` warns → don't. `map(..., strict=True)`. `int()` ignores `__trunc__`.
- **Stdlib:** `compression.zstd` (+ `compression.gzip/bz2/lzma/zlib`); `concurrent.interpreters` + `InterpreterPoolExecutor` (isolated multi-core); `Path.copy_into/move_into`, `Path.info`; `uuid.uuid6/8`, `uuid.NIL/MAX`; `heapq.heapify_max/heappush_max/heappop_max`; `functools.Placeholder`; `operator.is_none/is_not_none`; `date.strptime`, `time.strptime`; `io.Reader`/`io.Writer` (not `typing.IO/TextIO/BinaryIO`); `float/Decimal/Fraction.from_number`; `contextvars.Token` as context manager; `Executor.map(buffersize=)`; `unittest` `assertHasAttr`, `assertIsSubclass`, `assertStartsWith/EndsWith`; regex `\z`; `argparse(suggest_on_error=True, color=True)`; `python -m json`; pickle protocol 5 default.
- **Removed:** `ast.Num/Str/Bytes/NameConstant/Ellipsis` (→ `ast.Constant`); asyncio child watchers; itertools pickling; `pkgutil.find_loader/get_loader` (→ `importlib.util.find_spec`); `pty.master_open/slave_open`; `urllib.request.URLopener/FancyURLopener`; `sqlite3.version`; `importlib.abc.ResourceReader/Traversable/TraversableResources` (→ `importlib.resources.abc`).
- **Deprecated:** asyncio policy API (→ `asyncio.run(main(), loop_factory=...)`), `asyncio.iscoroutinefunction` (→ `inspect`), `codecs.open` (→ `open`), `os.popen`/`os.spawn*` (→ `subprocess`), `PurePath.as_uri`, `argparse.FileType`.
- **Behavior:** multiprocessing defaults to `forkserver` on non-macOS Unix: workers inherit no state → picklable callables, or `multiprocessing.get_context("fork")` when fork needed. `functools.partial` is a method descriptor. `Union[int, str] == int | str`.

### 3.15
- **Language:** lazy imports (also `lazy from x import y`): heavy, optionally used deps; module scope only (not functions, classes, `try`), not `*` or `__future__`. Cross-version: `__lazy_modules__ = ["json"]`. `frozendict`: hashable if contents are, not a `dict` subclass (check `isinstance(x, (dict, frozendict))` or `Mapping`). `sentinel` usable in `X | MISSING`. Comprehension unpacking also `{**d for d in dicts}`, `(*L for L in lists)`. `bytearray.take_bytes()` (no copy). `case +1:` in match.
- **Typing:** `TypedDict(closed=True)` / `extra_items=`; `TypeForm[T]` for params taking type expressions; `@disjoint_base`.
- **Stdlib:** `asyncio.TaskGroup.cancel()`; `profiling.tracing` / `profiling.sampling` (sampling, attach by PID), `profile` deprecated; `math.integer` module, `math.fmax/fmin/signbit/isnormal`; `Counter` `^`; `@contextmanager` decorators stay open across generators/coroutines; `threading.synchronized_iterator()`, `concurrent_tee()`; `json.loads(array_hook=)` (+ `frozendict` → fully immutable); `os.makedirs(parent_mode=)`; `pprint(expand=True)`; `tomllib` reads TOML 1.1; `unicodedata.iter_graphemes()`; `urlsplit(missing_as_none=True)`; `base64` `padded=`/`wrapcol=`/`canonical=`; `ssl.SSLContext.set_groups()`.
- **Removed:** `sre_compile/sre_constants/sre_parse`; `glob.glob0/glob1`; `CGIHTTPRequestHandler`; `Loader.load_module()`; `PurePath.is_reserved()` (→ `os.path.isreserved`); `platform.java_ver()`; `co_lnotab`; `typing.no_type_check_decorator`; `NamedTuple("P", x=int)` and `TypedDict("TD")` forms; AST constructors raise on missing/unknown fields; `strptime` with `%d` and no year raises.
- **Behavior:** UTF-8 default encoding for `open()` etc.; below 3.15 pass `encoding=` (default follows locale). `sqlite3.connect()` args after `database` keyword-only. `assertWarns` no longer swallows non-matching warnings. `importlib.metadata.metadata()` raises `MetadataNotFound`. Stdlib `__version__` deprecated.

## Step 3: Judgment

- **Scope:** modern idioms in all code you write or substantially rewrite, incl. new code in old-style file (new method among `Optional[...]` still gets `X | None`). Leave unrelated code: bug fix + 300 reformatted hint lines = unreviewable. Very dated file → mention once `ruff check --select UP --target-version pyXY --fix`. User asks to modernize → file-wide.
- **Above target would help** (3.11, `TaskGroup.cancel()`): cite as reason to raise floor; don't use.
- **Removed API** at/below target in code you write/touch: replace; it crashes.
- **Deprecated** at target: don't introduce; flag existing uses in touched code.
- **Clarity over novelty:** `match` for two-branch `if` = no gain; t-strings don't replace f-strings; lazy imports only for heavy optional deps.
- **Opt-in runtime** (free-threading, JIT, subinterpreters): needs project buy-in; mention only when it solves the user's actual problem.

## Tooling

Adding/changing config: ruff `target-version = "pyXY"`, mypy `python_version`, pyright `pythonVersion`, lowest CI matrix entry all = target. Linters then catch too-new syntax.

## Reporting

Don't narrate the skill. At most one line, e.g. "Targeting 3.12 (requires-python in pyproject.toml)", only when it shaped the code, target was guessed, or a conflict needs attention.
