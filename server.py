"""
CAS Journal MCP Server
中科院期刊分区（新锐分区）+ JCR影响因子 查询服务

Data source: ShowJCR (hitfyd/ShowJCR)
- FQBJCR2025: 中科院分区表升级版 2025
- JCR2024: JCR影响因子 2024
- GJQKYJMD2025: 国际期刊预警名单 2025
"""

import os
import sys
# Suppress FastMCP banner — must be set BEFORE importing fastmcp
os.environ['FASTMCP_QUIET'] = '1'

import pandas as pd
from fastmcp import FastMCP

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# ── Load data on startup ──────────────────────────────────────────
def load_data():
    """Load and join all data sources."""
    cas_path = os.path.join(DATA_DIR, "FQBJCR2025-UTF8.csv")
    jcr_path = os.path.join(DATA_DIR, "JCR2024-UTF8.csv")
    warn_path = os.path.join(DATA_DIR, "GJQKYJMD2025.csv")

    # Load CAS分区
    cas = pd.read_csv(cas_path, encoding='utf-8')
    cas.columns = [
        'Journal', 'Year', 'ISSN_EISSN', 'Review', 'OA_Index', 'Open_Access',
        'WoS', 'Note', '大类', '大类分区', 'Top',
        '小类1', '小类1分区', '小类2', '小类2分区', '小类3', '小类3分区',
        '小类4', '小类4分区', '小类5', '小类5分区', '小类6', '小类6分区'
    ]

    # Load JCR影响因子
    jcr = pd.read_csv(jcr_path, encoding='utf-8')
    jcr.columns = ['Journal', 'ISSN', 'eISSN', 'Category', 'IF_2024',
                   'IF_Quartile_2024', 'IF_Rank_2024']

    # Load 预警名单
    warn = pd.read_csv(warn_path, encoding='utf-8')
    warn_set = set(warn['Journal'].str.lower().str.strip())

    # Join on lowercased journal name
    cas['_key'] = cas['Journal'].str.lower().str.strip()
    jcr['_key'] = jcr['Journal'].str.lower().str.strip()

    # Merge: left join CAS ← JCR
    merged = cas.merge(jcr[['_key', 'IF_2024', 'IF_Quartile_2024', 'IF_Rank_2024', 'Category']],
                       on='_key', how='left')
    merged['预警'] = merged['_key'].isin(warn_set)
    merged['预警原因'] = merged['_key'].apply(
        lambda k: next((w for w in warn_set if w == k), '')
    )

    # Build lookup dict: key → best match row
    lookup = {}
    for _, row in merged.iterrows():
        key = row['_key']
        # Keep first match (CAS data already deduplicated)
        if key not in lookup:
            lookup[key] = row

    # Also index by ISSN
    issn_lookup = {}
    for _, row in merged.iterrows():
        issn_str = str(row.get('ISSN_EISSN', ''))
        for issn in issn_str.split('/'):
            issn = issn.strip()
            if issn and len(issn) > 4:
                issn_lookup[issn.lower()] = row['_key']

    return merged, lookup, issn_lookup, warn_set

print("Loading journal data...", file=sys.stderr)
df, lookup, issn_lookup, warn_set = load_data()
print(f"Loaded {len(lookup)} journals ({len(issn_lookup)} ISSNs), {len(warn_set)} warnings", file=sys.stderr)

# ── Load Chinese journal data (CNKI) ─────────────────────────────────
def load_cnki_data():
    """Load CNKI Chinese journal dataset with domestic rankings."""
    cnki_path = os.path.join(DATA_DIR, "CNKI-journals-UTF8.csv")
    if not os.path.exists(cnki_path):
        print(f"CNKI data not found at {cnki_path}, Chinese journal search disabled", file=sys.stderr)
        return {}, {}, pd.DataFrame()

    cn = pd.read_csv(cnki_path, encoding='utf-8')
    # Normalize NaN to empty string for text fields
    for col in ['ISSN', 'CN', 'Publisher', 'Frequency', 'Language', 'Discipline', 'SubDiscipline']:
        if col in cn.columns:
            cn[col] = cn[col].fillna('')
    # IF columns: keep as float, NaN means no IF available
    cn['IF_Composite'] = pd.to_numeric(cn['IF_Composite'], errors='coerce')
    cn['IF_Comprehensive'] = pd.to_numeric(cn['IF_Comprehensive'], errors='coerce')

    # Build lookup dict by lowercased journal name
    cn['_key'] = cn['Journal'].str.lower().str.strip()
    cn_lookup = {}
    for _, row in cn.iterrows():
        key = row['_key']
        if key not in cn_lookup:
            cn_lookup[key] = row

    # Build ISSN lookup
    cn_issn_lookup = {}
    for _, row in cn.iterrows():
        issn_str = str(row.get('ISSN', ''))
        for issn in issn_str.split('/'):
            issn = issn.strip().replace('-', '')
            if issn and len(issn) > 4:
                cn_issn_lookup[issn.lower()] = row['_key']

    return cn, cn_lookup, cn_issn_lookup

cn_df, cn_lookup, cn_issn_lookup = load_cnki_data()
cn_available = len(cn_lookup) > 0
print(f"Loaded {len(cn_lookup)} Chinese journals ({len(cn_issn_lookup)} ISSNs) from CNKI", file=sys.stderr)

# ── MCP Server ────────────────────────────────────────────────────
mcp = FastMCP(
    "CAS Journal MCP",
    instructions="中科院期刊分区（新锐分区）及JCR影响因子查询服务"
)


def format_journal(row) -> str:
    """Format a journal row as readable text."""
    lines = []
    lines.append(f"[ {row['Journal']}")
    lines.append(f"   ISSN: {row.get('ISSN_EISSN', 'N/A')}")
    lines.append(f"   WoS: {row.get('WoS', 'N/A')}")

    # CAS分区
    cas_major = row.get('大类', '')
    cas_rank = row.get('大类分区', '')
    is_top = row.get('Top', '否')
    top_mark = ' [Top]Top期刊' if str(is_top).strip() == '是' else ''
    lines.append(f"   [CAS] 中科院大类: {cas_major} | {cas_rank}{top_mark}")

    # 小类
    for i in range(1, 7):
        subj = row.get(f'小类{i}', '')
        subj_rank = row.get(f'小类{i}分区', '')
        if pd.notna(subj) and str(subj).strip():
            lines.append(f"      小类{i}: {subj} | {subj_rank}")

    # JCR IF
    if_val = row.get('IF_2024', None)
    if pd.notna(if_val):
        jcr_q = row.get('IF_Quartile_2024', '')
        jcr_rank = row.get('IF_Rank_2024', '')
        lines.append(f"   [IF] JCR IF(2024): {if_val} | {jcr_q} | Rank: {jcr_rank}")
    else:
        lines.append(f"   [IF] JCR IF(2024): 无（可能为AHCI/ESCI期刊或未被JCR收录）")

    # 预警
    if row.get('预警', False):
        lines.append(f"   [!] 预警期刊！预警原因: {row.get('预警原因', '未知')}")

    # OA
    oa = row.get('Open_Access', '')
    review = row.get('Review', '')
    lines.append(f"   [OA] OA: {oa} | 评审: {review}")

    return '\n'.join(lines)


def search_journal_fast(query: str, top_n: int = 10):
    """Fast fuzzy search by journal name."""
    query_lower = query.lower().strip()

    # Exact match first
    if query_lower in lookup:
        return [(query_lower, lookup[query_lower])]

    # Prefix match (for partial name)
    results = []
    for key, row in lookup.items():
        if query_lower in key:
            results.append((key, row))
            if len(results) >= top_n * 3:
                break

    # Sort: prefer shorter names (exact-ish), then alphabetically
    results.sort(key=lambda x: (len(x[0]), x[0]))
    return results[:top_n]


@mcp.tool()
def search_journal(name: str, top_n: int = 5) -> str:
    """通过期刊名称搜索中科院分区和JCR影响因子。

    支持中英文期刊名，支持部分匹配。
    返回：中科院大类/小类分区、Top期刊标识、JCR影响因子(2024)、
    JCR分区、预警状态等。

    Args:
        name: 期刊名称（支持部分匹配，不区分大小写）
        top_n: 返回的最大结果数（默认5）
    """
    results = search_journal_fast(name, top_n)
    if not results:
        return f"未找到与 '{name}' 匹配的期刊。请尝试更完整的名称。"

    lines = [f"找到 {len(results)} 条结果（查询: '{name}'）：\n"]
    for key, row in results:
        lines.append(format_journal(row))
        lines.append('')
    return '\n'.join(lines)


@mcp.tool()
def search_by_issn(issn: str) -> str:
    """通过ISSN号查询期刊信息。

    Args:
        issn: 期刊ISSN号（如 0028-0836）
    """
    key = issn_lookup.get(issn.strip().lower())
    if key is None:
        return f"未找到 ISSN '{issn}' 对应的期刊。"
    row = lookup[key]
    return format_journal(row)


@mcp.tool()
def compare_journals(names: str) -> str:
    """对比多个期刊的中科院分区和影响因子。

    Args:
        names: 期刊名称列表，用英文逗号分隔（如 "Nature,Science,Cell"）
    """
    journals = [n.strip() for n in names.split(',') if n.strip()]
    if not journals:
        return "请提供至少一个期刊名称。"

    lines = [f"[IF] 期刊对比（{len(journals)}本）：\n"]
    table_lines = []
    table_lines.append(f"{'期刊':<30} {'中科院大类':<15} {'大类分区':<8} {'Top':<4} {'IF(2024)':<10} {'JCR分区':<8} {'预警':<4}")
    table_lines.append('-' * 85)

    for name in journals:
        results = search_journal_fast(name, 1)
        if not results:
            table_lines.append(f"{name[:30]:<30} {'-- 未找到 --':>55}")
            continue
        _, row = results[0]
        journal_name = str(row['Journal'])[:28]
        cas_major = str(row.get('大类', ''))[:13]
        cas_rank = str(row.get('大类分区', ''))
        is_top = '是' if str(row.get('Top', '')).strip() == '是' else ''
        if_val_raw = row.get('IF_2024')
        if pd.notna(if_val_raw):
            try:
                if_val = f"{float(if_val_raw):.1f}"
            except (ValueError, TypeError):
                if_val = str(if_val_raw)
        else:
            if_val = 'N/A'
        jcr_q = str(row.get('IF_Quartile_2024', ''))
        warning = '[!]' if row.get('预警', False) else ''

        table_lines.append(f"{journal_name:<30} {cas_major:<15} {cas_rank:<8} {is_top:<4} {if_val:<10} {jcr_q:<8} {warning:<4}")

    lines.extend(table_lines)
    return '\n'.join(lines)


@mcp.tool()
def check_warning(name: str) -> str:
    """检查期刊是否在国际期刊预警名单中。

    Args:
        name: 期刊名称
    """
    results = search_journal_fast(name, 1)
    if not results:
        return f"未找到期刊 '{name}'。"

    _, row = results[0]
    if row.get('预警', False):
        # Try to get warning reason
        for w in warn_set:
            if w in row['_key']:
                return f"[!] **{row['Journal']}** 在2025年国际期刊预警名单中！\n   预警原因请参考官方名单。"
        return f"[!] **{row['Journal']}** 在2025年国际期刊预警名单中！"
    return f"[OK] **{row['Journal']}** 不在2025年国际期刊预警名单中。"


@mcp.tool()
def get_top_journals(field: str = "", top_n: int = 10) -> str:
    """按学科领域列出中科院Top期刊（大类1区+Top标识）。

    Args:
        field: 学科领域关键词（中英文均可，如"地理"/"geography"/"计算机"）
        top_n: 返回数量（默认10）
    """
    # Filter by field keyword
    mask = pd.Series(True, index=df.index)
    if field:
        field_lower = field.lower()
        mask = df['大类'].str.lower().str.contains(field_lower, na=False)

    # Top journals: 大类1区 OR Top=是
    top_mask = (df['大类分区'].astype(str).str.contains('1')) | (df['Top'].astype(str).str.strip() == '是')
    candidates = df[mask & top_mask].copy()

    if candidates.empty and field:
        return f"未找到学科 '{field}' 相关的Top期刊。请尝试其他关键词。"

    # Sort by IF descending
    candidates = candidates.sort_values('IF_2024', ascending=False, na_position='last').head(top_n)

    lines = [f"[Top] 中科院Top期刊（{'学科: ' + field if field else '全部领域'}，IF排序前{top_n}）：\n"]
    for _, row in candidates.iterrows():
        if_val_raw2 = row.get('IF_2024')
        if pd.notna(if_val_raw2):
            try:
                if_val = f"IF={float(if_val_raw2):.1f}"
            except (ValueError, TypeError):
                if_val = f"IF={if_val_raw2}"
        else:
            if_val = ''
        is_top = '[Top]' if str(row.get('Top', '')).strip() == '是' else f"{row.get('大类分区', '')}区"
        lines.append(f"  {row['Journal'][:50]:<52} {row.get('大类', '')[:20]:<20} {is_top:<6} {if_val}")

    return '\n'.join(lines)


# ── Chinese Journal Tools ───────────────────────────────────────────

def format_cn_journal(row) -> str:
    """Format a Chinese journal row with domestic ranking info."""
    lines = []
    lines.append(f"[ {row['Journal']}")

    issn = row.get('ISSN', '')
    cn_code = row.get('CN', '')
    lines.append(f"   ISSN: {issn if pd.notna(issn) and issn else 'N/A'} | CN: {cn_code if pd.notna(cn_code) and cn_code else 'N/A'}")

    publisher = row.get('Publisher', '')
    if pd.notna(publisher) and publisher:
        lines.append(f"   主办: {publisher}")

    # Language & founding year
    lang = row.get('Language', '')
    founded = row.get('Founded', '')
    freq = row.get('Frequency', '')
    lines.append(f"   语种: {lang if pd.notna(lang) and lang else '--'} | 周期: {freq if pd.notna(freq) and freq else '--'} | 创刊: {int(founded) if pd.notna(founded) and founded != '' else '--'}")

    # Domestic rankings
    ranking_parts = []
    if row.get('CSCD_Core'):
        ranking_parts.append('CSCD核心')
    if row.get('CSCD_Extended'):
        ranking_parts.append('CSCD扩展')
    if row.get('PKU_Core'):
        ranking_parts.append('北大核心')
    if row.get('CSSCI'):
        ranking_parts.append('CSSCI来源')
    if row.get('CSSCI_Extended'):
        ranking_parts.append('CSSCI扩展')
    if row.get('AMI_Authority'):
        ranking_parts.append('AMI权威')
    if row.get('AMI_Core'):
        ranking_parts.append('AMI核心')
    if row.get('AMI_Extended'):
        ranking_parts.append('AMI扩展')
    if row.get('AMI_Archive'):
        ranking_parts.append('AMI入库')
    if row.get('SCI_Indexed'):
        ranking_parts.append('SCI')
    if row.get('EI_Indexed'):
        ranking_parts.append('EI')
    if row.get('CSTPCD'):
        ranking_parts.append('中国科技核心')

    if ranking_parts:
        lines.append(f"   [国内分级] {', '.join(ranking_parts)}")
    else:
        lines.append(f"   [国内分级] 无核心标识")

    # CNKI Impact Factors
    if_comp = row.get('IF_Composite')
    if_comp2 = row.get('IF_Comprehensive')
    if pd.notna(if_comp) and if_comp > 0:
        lines.append(f"   [CNKI-IF] 复合IF: {float(if_comp):.3f} | 综合IF: {float(if_comp2):.3f}")
    else:
        lines.append(f"   [CNKI-IF] 暂无影响因子")

    # Discipline
    disc = row.get('Discipline', '')
    subdisc = row.get('SubDiscipline', '')
    if pd.notna(disc) and disc:
        lines.append(f"   [学科] {disc} | {subdisc if pd.notna(subdisc) and subdisc else ''}")

    return '\n'.join(lines)


def search_cn_journal_fast(query: str, top_n: int = 10):
    """Fast search in CNKI journal lookup dict."""
    query_lower = query.lower().strip()
    if not cn_available:
        return []

    # Exact match
    if query_lower in cn_lookup:
        return [(query_lower, cn_lookup[query_lower])]

    # Substring match
    results = []
    for key, row in cn_lookup.items():
        if query_lower in key:
            results.append((key, row))
            if len(results) >= top_n * 3:
                break

    results.sort(key=lambda x: (len(x[0]), x[0]))
    return results[:top_n]


@mcp.tool()
def search_cn_journal(name: str, top_n: int = 5) -> str:
    """搜索中文期刊的国内分级信息（CSCD、北大核心、CSSCI、AMI等）和CNKI影响因子。

    覆盖中国知网(CNKI)收录的中文学术期刊，返回：
    - CSCD（中国科学引文数据库）核心/扩展
    - 北大核心（北京大学《中文核心期刊要目总览》）
    - CSSCI（中文社会科学引文索引/南大核心）
    - AMI（中国人文社会科学期刊评价）
    - CNKI复合影响因子和综合影响因子

    Args:
        name: 期刊名称（支持部分匹配，中英文均可，不区分大小写）
        top_n: 返回的最大结果数（默认5）
    """
    if not cn_available:
        return "中文期刊数据未加载。请确保 data/CNKI-journals-UTF8.csv 存在。"

    results = search_cn_journal_fast(name, top_n)
    if not results:
        return f"未找到与 '{name}' 匹配的中文期刊。请尝试更完整的名称。"

    lines = [f"找到 {len(results)} 条中文期刊结果（查询: '{name}'）：\n"]
    for key, row in results:
        lines.append(format_cn_journal(row))
        lines.append('')
    return '\n'.join(lines)


@mcp.tool()
def search_cn_by_issn(issn: str) -> str:
    """通过ISSN号查询中文期刊的国内分级信息。

    Args:
        issn: 期刊ISSN号（如 0375-5444）
    """
    if not cn_available:
        return "中文期刊数据未加载。"
    issn_clean = issn.strip().replace('-', '').lower()
    key = cn_issn_lookup.get(issn_clean)
    if key is None:
        return f"未找到 ISSN '{issn}' 对应的中文期刊。"
    row = cn_lookup[key]
    return format_cn_journal(row)


@mcp.tool()
def get_cn_core_journals(field: str = "", system: str = "all", top_n: int = 20) -> str:
    """按学科领域和分级系统列出中文核心期刊。

    Args:
        field: 学科关键词（如"地理"/"计算机"/"经济"），留空为全部学科
        system: 分级系统 —
            "cscd" = CSCD核心期刊
            "pku" = 北大核心期刊
            "cssci" = CSSCI来源期刊
            "ami" = AMI核心及以上
            "all" = 任一核心期刊（默认）
        top_n: 返回数量（默认20），按CNKI复合IF降序排列
    """
    if not cn_available:
        return "中文期刊数据未加载。"

    mask = pd.Series(True, index=cn_df.index)

    # Filter by field
    if field:
        field_lower = field.lower()
        mask &= (cn_df['Discipline'].str.lower().str.contains(field_lower, na=False) |
                 cn_df['SubDiscipline'].str.lower().str.contains(field_lower, na=False))
        if not mask.any():
            # Try matching journal names too
            mask |= cn_df['Journal'].str.lower().str.contains(field_lower, na=False)

    # Filter by ranking system
    sys_map = {
        'cscd': 'CSCD_Core',
        'pku': 'PKU_Core',
        'cssci': 'CSSCI',
        'ami': 'AMI_Core',
    }

    if system in sys_map:
        col = sys_map[system]
        # For AMI, also include 权威
        if system == 'ami':
            mask &= (cn_df['AMI_Core'] | cn_df['AMI_Authority'])
        else:
            mask &= cn_df[col]
    elif system == 'all':
        mask &= (cn_df['CSCD_Core'] | cn_df['PKU_Core'] | cn_df['CSSCI'] |
                 cn_df['AMI_Core'] | cn_df['AMI_Authority'])

    candidates = cn_df[mask].copy()
    if candidates.empty:
        sys_name = {'cscd': 'CSCD核心', 'pku': '北大核心', 'cssci': 'CSSCI', 'ami': 'AMI核心/权威', 'all': '任一核心'}[system]
        return f"未找到学科 '{field}' 中属于 {sys_name} 的中文期刊。"

    # Sort by IF_Composite descending
    candidates = candidates.sort_values('IF_Composite', ascending=False, na_position='last').head(top_n)

    sys_name = {'cscd': 'CSCD核心', 'pku': '北大核心', 'cssci': 'CSSCI', 'ami': 'AMI核心/权威', 'all': '核心期刊'}[system]
    lines = [f"[中文核心] {sys_name}（{'学科: ' + field if field else '全部学科'}，按CNKI复合IF降序，前{top_n}）：\n"]

    for _, row in candidates.iterrows():
        # Build ranking badges
        badges = []
        if row.get('CSCD_Core'): badges.append('CSCD')
        if row.get('PKU_Core'): badges.append('北大核心')
        if row.get('CSSCI'): badges.append('CSSCI')
        if row.get('AMI_Authority'): badges.append('AMI权威')
        elif row.get('AMI_Core'): badges.append('AMI核心')

        if_comp = row.get('IF_Composite')
        if_val = f"IF={float(if_comp):.3f}" if pd.notna(if_comp) and if_comp > 0 else ''

        journal_name = str(row['Journal'])[:40]
        badges_str = ', '.join(badges)[:36]
        lines.append(f"  {journal_name:<42} {badges_str:<38} {if_val}")

    return '\n'.join(lines)


if __name__ == "__main__":
    mcp.run()
