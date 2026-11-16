#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 LeetCode 网页(leetcode.cn)同步「网页端做题记录」到本地仓库。

为什么需要它:
    auto_sync.sh 原本只监听本地 cn/ 目录的文件变化。但作者习惯在
    leetcode.cn 网页上做题 —— 代码留在 LeetCode 服务器, 本地不生成文件,
    于是自动同步永远看不到新题, 跑了也是空转。本脚本补上「拉」这一环。

登录态从哪来(全程不落盘 cookie 明文):
    Chrome 的 Cookie 库 ~/Library/Application Support/Google/Chrome/Default/Network/Cookies
    是加密的 SQLite; 用 macOS 钥匙串里的 "Chrome Safe Storage" 密钥,
    经 PBKDF2-HMAC-SHA1(pw, "saltysalt", 1003) 派生 AES key,
    再用系统 openssl 解 v10 前缀的密文(IV = 16 个空格)。

接口:
    GET  /api/submissions/              最近提交列表(不含题号)
    POST /graphql/  userStatus          校验登录态
    POST /graphql/  submissionDetail    一次拿到「题号 + 完整代码」(注意 ID! 类型)

行为:
    1. 拉最近 N 条提交, 只保留 Accepted
    2. 对本地还没有的题号, 抓代码写入 cn/[NNNN]标题.py
    3. 同一题存在多份不同代码时, 额外版本存到 cn/variants/[NNNN]-k标题.py
    4. 顺带补拉官方用例(调用 fetch_testcases.py)
    5. 登录态失效 / 钥匙串不可访问时, 打印明确提示并返回 0 —— 绝不阻断后续自动同步

用法:
    python3 tools/fetch_web_submissions.py              # 增量同步
    python3 tools/fetch_web_submissions.py --limit 100  # 多看些提交
    python3 tools/fetch_web_submissions.py --dry-run    # 只报告不写文件
"""

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CN_DIR = os.path.join(ROOT, "solutions", "leetcode", "editor", "cn")
VAR_DIR = os.path.join(CN_DIR, "variants")
COOKIE_DB = os.path.expanduser(
    "~/Library/Application Support/Google/Chrome/Default/Network/Cookies")
BASE = "https://leetcode.cn"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def log(msg):
    print("[web-sync] %s" % msg, flush=True)


# ---------- 取登录态(内存/管道, 不写盘) ----------
def load_cookies():
    if not os.path.exists(COOKIE_DB):
        raise RuntimeError("找不到 Chrome Cookie 库: %s" % COOKIE_DB)
    # 复制到临时文件读, 避免 Chrome 正占用导致锁
    tmp = "/tmp/.lc_cookie_readonly_%d.db" % os.getpid()
    with open(COOKIE_DB, "rb") as src, open(tmp, "wb") as dst:
        dst.write(src.read())
    try:
        con = sqlite3.connect(tmp)
        rows = con.execute(
            "SELECT host_key, name, encrypted_value FROM cookies "
            "WHERE host_key LIKE '%leetcode.cn%'").fetchall()
        con.close()
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass

    pw = subprocess.run(
        ["/usr/bin/security", "find-generic-password", "-w",
         "-s", "Chrome Safe Storage"],
        capture_output=True, text=True)
    if pw.returncode != 0 or not pw.stdout.strip():
        raise RuntimeError("钥匙串 Chrome Safe Storage 不可访问(可能被系统要求授权)")
    key = hashlib.pbkdf2_hmac("sha1", pw.stdout.strip().encode(),
                              b"saltysalt", 1003, dklen=16)
    iv = b" " * 16

    def decrypt(blob):
        if not blob:
            return ""
        if blob[:3] == b"v10":
            blob = blob[3:]
        if len(blob) % 16:
            blob += b"\x00" * (16 - len(blob) % 16)
        r = subprocess.run(
            ["/usr/bin/openssl", "enc", "-aes-128-cbc", "-d",
             "-K", key.hex(), "-iv", iv.hex()],
            input=blob, capture_output=True)
        if r.returncode != 0:
            return ""
        out = r.stdout
        # 新版 Chrome 在明文前加了 32 字节域名哈希
        if len(out) > 32:
            cand = out[32:]
            if all(32 <= c < 127 for c in cand[:8] if c):
                return cand.decode("utf-8", "ignore")
        return out.decode("utf-8", "ignore").lstrip("\x00")

    cookies = {}
    for host, name, enc in rows:
        val = decrypt(enc)
        if val and (name not in cookies or host == ".leetcode.cn"):
            cookies[name] = val
    if "LEETCODE_SESSION" not in cookies:
        raise RuntimeError("Chrome 里没有 leetcode.cn 的 LEETCODE_SESSION, 请在浏览器重新登录 leetcode.cn")
    return cookies


def make_session(cookies):
    hdr = {
        "User-Agent": UA,
        "Cookie": "; ".join("%s=%s" % (k, v) for k, v in cookies.items()),
        "Referer": BASE + "/",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": BASE,
        "x-csrftoken": cookies.get("csrftoken", ""),
        "x-requested-with": "XMLHttpRequest",
    }

    def get(url):
        req = urllib.request.Request(url, headers=hdr)
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))

    def gql(query, variables=None):
        payload = json.dumps({"query": query, "variables": variables or {}}).encode()
        req = urllib.request.Request(BASE + "/graphql/", data=payload, headers=hdr)
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))

    return get, gql


DETAIL_QUERY = """query submissionDetail($submissionId: ID!) {
  submissionDetail(submissionId: $submissionId) {
    code lang statusDisplay
    question { questionFrontendId translatedTitle titleSlug }
  }
}"""


def local_ids():
    ids = set()
    if os.path.isdir(CN_DIR):
        for fn in os.listdir(CN_DIR):
            m = re.match(r"^\[(\d+)\]", fn)
            if m:
                ids.add(int(m.group(1)))
    return ids


def norm_code(c):
    """比较两份代码是否实质相同: 去掉空行/行尾空白/注释行。"""
    lines = [ln.rstrip() for ln in (c or "").splitlines()]
    return "\n".join(ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#"))


def main():
    # 每天定点扫描只看最近 20 条足够(一天做不了更多), 请求少也就不容易触发限流
    limit = 20
    dry = "--dry-run" in sys.argv
    if "--limit" in sys.argv:
        try:
            limit = int(sys.argv[sys.argv.index("--limit") + 1])
        except (ValueError, IndexError):
            pass

    try:
        cookies = load_cookies()
        get, gql = make_session(cookies)
    except Exception as e:
        log("跳过网页同步: %s" % e)
        log("  → 修复办法: 在 Chrome 里打开并登录 leetcode.cn, 然后重跑本脚本")
        return 0

    try:
        status = (gql("query { userStatus { isSignedIn username } }")
                  .get("data", {}).get("userStatus", {}))
        if not status.get("isSignedIn"):
            log("跳过网页同步: LeetCode 登录态已失效")
            log("  → 修复办法: 在 Chrome 里重新登录 leetcode.cn (会话过期后需重新登录)")
            return 0
        log("登录态有效: %s" % status.get("username"))
    except Exception as e:
        log("跳过网页同步: 无法校验登录态 (%s)" % e)
        return 0

    try:
        subs = get(BASE + "/api/submissions/?offset=0&limit=%d" % limit).get(
            "submissions_dump", [])
    except Exception as e:
        log("跳过网页同步: 拉取提交列表失败 (%s)" % e)
        return 0
    log("最近提交 %d 条" % len(subs))

    existing = local_ids()
    # 结果缓存: 已成功抓过详情的 submission id 不再重复请求, 大幅降低限流概率
    cache_file = os.path.join(ROOT, "tools", ".cache", "web_submissions.json")
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    try:
        cache = json.load(open(cache_file, encoding="utf-8"))
    except Exception:
        cache = {}
    # 结构: {sub_id: {"fid": 题号, "title": 标题, "code": 代码}}
    cache = {str(k): v for k, v in cache.items() if isinstance(v, dict)}

    by_qid = {}       # 题号 -> [(sub_id, code, title), ...]
    seen_ids = set()
    newly_fetched = 0
    for s in subs:
        if s.get("status_display") != "Accepted":
            continue
        sid = str(s.get("id") or "")
        if not sid or sid in seen_ids:
            continue
        seen_ids.add(sid)
        if sid in cache and isinstance(cache[sid].get("code"), str) and cache[sid]["code"].strip():
            c = cache[sid]
            if str(c.get("fid", "")).isdigit():
                by_qid.setdefault(int(c["fid"]), []).append(
                    (sid, c["code"], c.get("title") or ""))
                continue
        # LeetCode 偶发对单个提交返回 405/限流, 简单退避重试, 避免整轮少算题
        d = {}
        for attempt in range(3):
            try:
                d = (gql(DETAIL_QUERY, {"submissionId": str(sid)})
                     .get("data", {}).get("submissionDetail") or {})
                if d:
                    break
            except Exception as e:
                if attempt == 2:
                    log("  提交 %s 详情失败(已重试3次): %s" % (sid, e))
                else:
                    time.sleep(0.8 * (attempt + 1))
        if not d:
            continue
        q = d.get("question") or {}
        fid = str(q.get("questionFrontendId") or "")
        code = d.get("code") or ""
        if not fid.isdigit() or not code.strip():
            continue
        title = q.get("translatedTitle") or s.get("title") or ""
        cache[sid] = {"fid": fid, "title": title, "code": code}
        newly_fetched += 1
        by_qid.setdefault(int(fid), []).append((sid, code, title))
        # 每次详情请求后歇一下: LeetCode 对短时间高频 GraphQL 会限流返回空/405
        time.sleep(0.6)

    if newly_fetched:
        try:
            # 只保留最近 300 条, 避免缓存无限膨胀
            keep = dict(list(cache.items())[-300:])
            json.dump(keep, open(cache_file, "w", encoding="utf-8"),
                      ensure_ascii=False)
            log("缓存命中, 本轮新请求 %d 条详情" % newly_fetched)
        except Exception as e:
            log("写缓存失败(不影响同步): %s" % e)

    # 限流兜底: 若一条详情都没拿到, 明确报告"本轮未取到数据", 不要误判成"没有新题"
    if not by_qid:
        log("本轮未取到任何提交详情(疑似接口限流), 判定为『未知』而非『无新题』, 下次会自动重试")
        return 0

    new_ids, variant_ids = [], []
    for fid in sorted(by_qid):
        versions = by_qid[fid]
        # 去重: 同一题可能重复提交相同代码
        uniq, seen_code = [], set()
        for sid, code, title in versions:
            key = norm_code(code)
            if key and key not in seen_code:
                seen_code.add(key)
                uniq.append((sid, code, title))
        title = re.sub(r'[/\\:*?"<>|]', "", uniq[0][2]).strip() or "untitled"
        # 文件名里的空格/反斜杠会让 shell 与 git 显示成 "2\ 的幂" 这类转义, 统一收敛
        title = re.sub(r"\s+", "", title)

        if fid not in existing:
            log("  ★ 新题 %-5s %s (提交 %d 次, %d 种解法)" % (
                fid, title, len(versions), len(uniq)))
            new_ids.append(fid)
            if not dry:
                path = os.path.join(CN_DIR, "[%04d]%s.py" % (fid, title))
                with open(path, "w", encoding="utf-8") as f:
                    f.write(uniq[0][1].rstrip() + "\n")
        # 多解法: 额外的版本按 -1 / -2 编号存入 variants/
        # 注意: uniq 来自「最近提交列表」(新→旧), 所以 -1 是后提交的那版、-2 是先提交的,
        #       编号不是时间正序; 讲解文档开头有「真实提交时间线」小节说明真实先后。
        if len(uniq) > 1:
            variant_ids.append(fid)
            if not dry:
                os.makedirs(VAR_DIR, exist_ok=True)
                for i, (sid, code, _) in enumerate(uniq, 1):
                    p = os.path.join(VAR_DIR, "[%04d]-%d-%s.py" % (fid, i, title))
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(code.rstrip() + "\n")

    if not new_ids:
        log("没有发现新题, 本地已是最新")
    else:
        log("共写入 %d 道新题" % len(new_ids))
        if not dry:
            # 补拉官方用例, 让 local_run.py 也能直接跑新题
            script = os.path.join(ROOT, "tools", "fetch_testcases.py")
            if os.path.exists(script):
                try:
                    subprocess.run([sys.executable, script] +
                                   [str(i) for i in new_ids],
                                   timeout=180, capture_output=True)
                    log("已补拉官方用例")
                except Exception as e:
                    log("补拉用例失败(不影响代码同步): %s" % e)
    if variant_ids:
        log("存在多种解法的题号(已按 -1/-2 存到 variants/): %s" % variant_ids)
    return 0


if __name__ == "__main__":
    sys.exit(main())
