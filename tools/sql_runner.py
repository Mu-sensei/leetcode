#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQL 类题目（LeetCode 数据库题）的本地执行引擎。

用户写的是 MySQL 方言，这里做方言适配后用真实数据库执行：
    - PostgreSQL 优先（若本机已安装）
    - SQLite 兜底（Python 标准库自带，零安装，保证任何机器都能跑）

流程：官方 DDL 建表 -> 灌入官方示例数据 -> 执行用户的 SQL -> 与官方结果表比对。
"""

import os
import re
import shutil
import sqlite3
import subprocess
import time

PGDATA = os.path.expanduser("~/.cache/leetcode_pg")
PGPORT = "5433"
PGLOG = os.path.join(PGDATA, "server.log")


# ---------------------------------------------------------------- 环境探测
def pg_bin():
    """找到 PostgreSQL 的 bin 目录，找不到返回 None。"""
    cands = []
    for v in ("17", "16", "15", "14"):
        cands.append("/usr/local/opt/postgresql@%s/bin" % v)
        cands.append("/opt/homebrew/opt/postgresql@%s/bin" % v)
    cands.append("/Applications/Postgres.app/Contents/Versions/latest/bin")
    cands.append("/usr/local/bin")
    cands.append("/usr/bin")
    for d in cands:
        if os.path.exists(os.path.join(d, "initdb")) and os.path.exists(os.path.join(d, "psql")):
            return d
    exe = shutil.which("psql")
    if exe and os.path.exists(os.path.join(os.path.dirname(exe), "initdb")):
        return os.path.dirname(exe)
    return None


def pg_available():
    return pg_bin() is not None


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def pg_ensure_running():
    """确保本地 PG 实例在运行（首次会自动 initdb）。成功返回 bin 目录，失败返回 None。"""
    b = pg_bin()
    if not b:
        return None
    if not os.path.exists(os.path.join(PGDATA, "PG_VERSION")):
        os.makedirs(PGDATA, exist_ok=True)
        r = _run([os.path.join(b, "initdb"), "-D", PGDATA,
                  "-U", "postgres", "--auth=trust", "-E", "UTF8"])
        if r.returncode != 0:
            print("    [!] initdb 失败:", (r.stderr or "").strip()[:200])
            return None
    for _ in range(40):
        r = _run([os.path.join(b, "pg_isready"), "-h", "/tmp", "-p", PGPORT])
        if r.returncode == 0:
            return b
        _run([os.path.join(b, "pg_ctl"), "-D", PGDATA, "-l", PGLOG,
              "-o", "-p %s -k /tmp -c listen_addresses=''" % PGPORT, "start"])
        time.sleep(0.5)
    print("    [!] PostgreSQL 启动超时，回退 SQLite")
    return None


# ---------------------------------------------------------------- 方言适配
_DEL_JOIN = re.compile(
    r"^\s*DELETE\s+(?P<a1>\w+)\s+FROM\s+(?P<from>.+?)\s+JOIN\s+(?P<join>.+?)"
    r"\s+ON\s+(?P<on>.+?)\s*;?\s*$", re.I | re.S)


def to_pg(sql):
    """MySQL -> PostgreSQL。"""
    s = sql
    s = re.sub(r"DATE_ADD\s*\(\s*([^,]+?)\s*,\s*INTERVAL\s+(\d+)\s+DAY\s*\)",
               r"(\1 + INTERVAL '\2 day')", s, flags=re.I)
    s = re.sub(r"DATE_SUB\s*\(\s*([^,]+?)\s*,\s*INTERVAL\s+(\d+)\s+DAY\s*\)",
               r"(\1 - INTERVAL '\2 day')", s, flags=re.I)
    s = re.sub(r"DATEDIFF\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
               r"(\1 - \2)", s, flags=re.I)
    s = re.sub(r"IFNULL\s*\(", "COALESCE(", s, flags=re.I)
    # 注意: PG 会把未加引号的标识符折叠成小写, 若转成 "Name" 反而不匹配建表时的 name,
    # 所以这里直接去掉反引号, 沿用 PG 默认的大小写不敏感行为。
    s = s.replace("`", "")
    m = _DEL_JOIN.match(s)
    if m:
        s = "DELETE FROM %s USING %s WHERE %s" % (
            m.group("from"), m.group("join"), m.group("on"))
    return s


def to_sqlite(sql):
    """MySQL -> SQLite。"""
    s = sql
    s = re.sub(r"DATE_ADD\s*\(\s*([^,]+?)\s*,\s*INTERVAL\s+(\d+)\s+DAY\s*\)",
               r"date(\1, '+\2 day')", s, flags=re.I)
    s = re.sub(r"DATE_SUB\s*\(\s*([^,]+?)\s*,\s*INTERVAL\s+(\d+)\s+DAY\s*\)",
               r"date(\1, '-\2 day')", s, flags=re.I)
    s = re.sub(r"DATEDIFF\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
               r"(julianday(\1) - julianday(\2))", s, flags=re.I)
    s = s.replace("`", "")
    m = _DEL_JOIN.match(s)
    if m:
        # SQLite 不支持多表 DELETE，改用 rowid 子查询
        main = m.group("from").split()[0]
        s = ("DELETE FROM %s WHERE rowid IN (SELECT %s.rowid FROM %s JOIN %s ON %s)"
             % (main, m.group("a1"), m.group("from"), m.group("join"), m.group("on")))
    return s


def to_dialect(sql, engine):
    return to_sqlite(sql) if engine == "sqlite" else to_pg(sql)


# ---------------------------------------------------------------- 用例准备
def extract_sql(path):
    """从解法文件里抠出用户写的 SQL（submit region 内的非注释行）。"""
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    body, inside = [], False
    for ln in lines:
        s = ln.strip()
        if "submit region begin" in s:
            inside = True
            continue
        if "submit region end" in s:
            inside = False
            continue
        if not inside or not s or s.startswith("#") or s.startswith("--"):
            continue
        body.append(s)
    return " ".join(body).strip().rstrip(";")


def _cell(v):
    """数据库返回值 -> Python 值（用于和官方期望比对）。"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return v
    s = str(v).strip()
    if s == "" or s.upper() in ("NULL", "\\N", "NONE"):
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        f = float(s)
        return int(f) if f.is_integer() else f
    except ValueError:
        pass
    return s


def _lit(v):
    """Python 值 -> SQL 字面量（仅用于生成 PG 脚本，数据都来自官方示例，可信）。"""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def table_of(ddl_stmt):
    m = re.search(r"table\s+(?:if\s+not\s+exists\s+)?(\w+)", ddl_stmt, re.I)
    return m.group(1) if m else None


def build_input(case_input):
    """用例输入 -> {表名: (列名列表, 行列表)}。"""
    data = None
    if isinstance(case_input, (list, tuple)):
        for x in case_input:
            if isinstance(x, dict) and "rows" in x:
                data = x
                break
    elif isinstance(case_input, dict):
        data = case_input
    if not data:
        return {}
    headers = data.get("headers") or {}
    rows = data.get("rows") or {}
    out = {}
    for t, vals in rows.items():
        out[t] = (headers.get(t) or [], [list(r) for r in vals])
    return out


# ---------------------------------------------------------------- SQLite 后端
def run_sqlite(ddl, tables, user_sql, dump_table):
    con = sqlite3.connect(":memory:")
    cur = con.cursor()
    for stmt in ddl:
        try:
            cur.execute(stmt)
        except sqlite3.Error as e:
            print("    [!] 建表失败: %s" % e)
            return None
    for t, (cols, rows) in tables.items():
        if not rows:
            continue
        ph = ", ".join("?" * len(rows[0]))
        collist = ("(%s)" % ", ".join(cols)) if cols else ""
        try:
            cur.executemany("INSERT INTO %s %s VALUES (%s)" % (t, collist, ph),
                            [list(r) for r in rows])
        except sqlite3.Error as e:
            print("    [!] 插入数据失败(%s): %s" % (t, e))
            return None
    con.commit()
    try:
        cur.execute(user_sql)
    except sqlite3.Error as e:
        print("    [!] SQL 执行出错: %s" % e)
        print("    实际执行: %s" % user_sql)
        return None
    res = cur.fetchall() if cur.description else None
    if res is None and dump_table:
        try:
            cur.execute("SELECT * FROM %s" % dump_table)
            res = cur.fetchall()
        except sqlite3.Error:
            res = None
    con.close()
    return None if res is None else [[_cell(c) for c in r] for r in res]


# ---------------------------------------------------------------- PostgreSQL 后端
def run_pg(b, ddl, tables, user_sql, dump_table):
    schema = "lc_run_%d" % os.getpid()
    script = ["DROP SCHEMA IF EXISTS %s CASCADE;" % schema,
              "CREATE SCHEMA %s;" % schema,
              "SET search_path TO %s;" % schema]
    script += [s.rstrip(";") + ";" for s in ddl]
    for t, (cols, rows) in tables.items():
        for r in rows:
            collist = ("(%s)" % ", ".join(cols)) if cols else ""
            script.append("INSERT INTO %s %s VALUES (%s);"
                          % (t, collist, ", ".join(_lit(v) for v in r)))
    script.append(user_sql.strip().rstrip(";") + ";")
    if dump_table:
        script.append("SELECT * FROM %s;" % dump_table)

    psql = os.path.join(b, "psql")
    raw = "\n".join(script).encode("utf-8")
    r = subprocess.run([psql, "-h", "/tmp", "-p", PGPORT, "-U", "postgres",
                        "-d", "postgres", "-v", "ON_ERROR_STOP=0",
                        "-X", "-q", "-A", "-F", "\x1f", "-t", "-f", "-"],
                       input=raw, capture_output=True)
    # 清理 schema
    subprocess.run([psql, "-h", "/tmp", "-p", PGPORT, "-U", "postgres", "-d", "postgres",
                    "-X", "-q", "-c", "DROP SCHEMA IF EXISTS %s CASCADE;" % schema],
                   capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    if r.returncode != 0 and not out.strip():
        err = r.stderr.decode("utf-8", "replace").strip()
        print("    [!] SQL 执行出错: %s" % err.split("\n")[0][:200])
        print("    实际执行: %s" % user_sql)
        return None
    rows = []
    for ln in out.split("\n"):
        if not ln.strip():
            continue
        if ln.startswith(("ERROR", "psql:", "HINT", "DETAIL", "LINE")):
            continue
        rows.append([_cell(c) for c in ln.split("\x1f")])
    return rows


# ---------------------------------------------------------------- 对外入口
def run_case(pid, path, info, case, engine="auto"):
    """跑一组 SQL 用例。返回 (是否通过, 实际结果)。"""
    ddl = info.get("ddl") or []
    tables = build_input(case.get("input"))
    user_sql_raw = extract_sql(path)
    if not user_sql_raw:
        print("    [!] 文件里没找到 SQL 语句")
        return False, None
    # DELETE/UPDATE 类: 结果不来自返回值, 而是执行完后的整张表
    verb = user_sql_raw.strip().split()[0].upper()
    dump_table = None
    if verb in ("DELETE", "UPDATE", "INSERT", "REPLACE"):
        dump_table = table_of(ddl[0]) if ddl else None

    b = None
    if engine in ("auto", "pg"):
        b = pg_ensure_running()
    if b:
        used = "PostgreSQL"
        sql = to_pg(user_sql_raw)
        got = run_pg(b, ddl, tables, sql, dump_table)
    else:
        used = "SQLite"
        sql = to_sqlite(user_sql_raw)
        got = run_sqlite(ddl, tables, sql, dump_table)

    if got is None:
        return False, None, used

    expected = case.get("output")
    exp_rows = None
    if isinstance(expected, dict):
        exp_rows = [[_cell(c) for c in r] for r in (expected.get("rows") or [])]

    if exp_rows is None:
        print("    [%s] ➖ 无官方期望输出, 仅执行 | 得到 %d 行" % (used, len(got)))
        return True, got, used

    def key(rs):
        return sorted([tuple(str(c) for c in r) for r in rs])

    ok = key(got) == key(exp_rows)
    return ok, got, used
