"""CLI for exploring the Korean National Assembly Bills dataset."""

from __future__ import annotations

import sys
import textwrap
from typing import Optional

import click
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from korean_assembly_bills.loader import (
    load_bills,
    load_mp_metadata,
    load_proposers,
    load_texts,
)

console = Console()

# ASCII art banner (figlet "assembly bills" style)
_BANNER_LINES = [
    r"                               _     _         _     _ _ _     ",
    r"   __ _ ___ ___  ___ _ __ ___ | |__ | |_   _  | |__ (_) | |___",
    r"  / _` / __/ __|/ _ \ '_ ` _ \| '_ \| | | | | | '_ \| | | / __|",
    r" | (_| \__ \__ \  __/ | | | | | |_) | | |_| | | |_) | | | \__ \\",
    r"  \__,_|___/___/\___|_| |_| |_|_.__/|_|\__, | |_.__/|_|_|_|___/",
    r"                                        |___/                   ",
]

# Gradient: teal -> cyan -> blue (matching open-assembly-mcp style)
_GRADIENT = [
    (0, 210, 190),
    (0, 195, 210),
    (30, 180, 225),
    (60, 165, 235),
    (90, 150, 240),
    (110, 140, 245),
]

_COLOR = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _bold_rgb(r: int, g: int, b: int, text: str) -> str:
    return f"\033[1;38;2;{r};{g};{b}m{text}\033[0m" if _COLOR else text


def _dim(text: str) -> str:
    return f"\033[2m{text}\033[0m" if _COLOR else text


def _print_banner() -> None:
    print()
    for i, line in enumerate(_BANNER_LINES):
        r, g, b = _GRADIENT[i % len(_GRADIENT)]
        print(_bold_rgb(r, g, b, line))
    print()
    print(_dim("  ────────────────────────────────────────────────────────────────"))
    print(
        f"  {_bold_rgb(0, 210, 190, 'assembly-bills')}"
        f"  {_dim('·')}  "
        f"{_dim('Korean National Assembly Bills Dataset')}"
    )
    print(
        f"  {_dim('20th-22nd Assembly  ·  60,925 bills  ·  with propose-reason texts')}"
    )
    print(_dim("  ────────────────────────────────────────────────────────────────"))
    print()


def _truncate(s: str, maxlen: int = 120) -> str:
    if pd.isna(s):
        return ""
    s = str(s).replace("\n", " ").strip()
    return s[:maxlen] + "..." if len(s) > maxlen else s


# ---------------------------------------------------------------------------
# Main group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(package_name="korean-assembly-bills")
def cli():
    """assembly-bills -- explore 60,925 Korean National Assembly bills from the terminal."""
    pass


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------

@cli.command()
def info():
    """Show dataset summary."""
    _print_banner()

    bills = load_bills(columns=["BILL_ID", "AGE", "PROPOSE_DT", "COMMITTEE", "PROC_RESULT"])
    texts = load_texts(columns=["BILL_ID", "scrape_status", "propose_reason"])

    table = Table(show_header=True, border_style="dim", pad_edge=False)
    table.add_column("", style="dim", width=24)
    table.add_column("", style="bold")

    table.add_row("total bills", f"{len(bills):,}")
    for age in sorted(bills["AGE"].unique()):
        n = (bills["AGE"] == age).sum()
        table.add_row(f"  {age}th assembly", f"{n:,}")

    table.add_row("date range", f"{bills['PROPOSE_DT'].min()} ~ {bills['PROPOSE_DT'].max()}")
    table.add_row("committees", f"{bills['COMMITTEE'].nunique()}")

    has_text = (texts["scrape_status"] == "ok").sum()
    table.add_row("texts available", f"{has_text:,} ({has_text / len(bills) * 100:.1f}%)")

    text_lens = texts.loc[texts["propose_reason"].notna(), "propose_reason"].str.len()
    table.add_row("text length (median)", f"{text_lens.median():.0f} chars")
    table.add_row("text length (mean)", f"{text_lens.mean():.0f} chars")

    console.print(table)
    console.print()


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("keyword")
@click.option("-n", "--limit", default=20, help="Max results (default 20)")
@click.option("--age", type=int, help="Filter by assembly (20, 21, 22)")
@click.option("--committee", help="Filter by committee name (substring)")
@click.option("--party", help="Filter by lead proposer party (substring)")
@click.option("--text", is_flag=True, help="Also search in propose-reason texts")
def search(keyword: str, limit: int, age: Optional[int], committee: Optional[str],
           party: Optional[str], text: bool):
    """Search bills by keyword.

    \b
    Examples:
      assembly-bills search "인공지능"
      assembly-bills search "부동산" --age 21 --committee 국토
      assembly-bills search "데이터" --text
    """
    bills = load_bills()
    mask = bills["BILL_NAME"].str.contains(keyword, case=False, na=False)

    if text:
        console.print("[dim]searching texts...[/dim]", end=" ")
        texts_df = load_texts(columns=["BILL_ID", "propose_reason"])
        text_mask = texts_df.set_index("BILL_ID")["propose_reason"].str.contains(
            keyword, case=False, na=False
        )
        text_ids = set(text_mask[text_mask].index)
        mask = mask | bills["BILL_ID"].isin(text_ids)

    if age:
        mask = mask & (bills["AGE"] == age)
    if committee:
        mask = mask & bills["COMMITTEE"].str.contains(committee, case=False, na=False)
    if party:
        mask = mask & bills["PROPOSER"].str.contains(party, case=False, na=False)

    total_matches = mask.sum()
    results = bills[mask].head(limit)

    if results.empty:
        console.print(f"[dim]no results for[/dim] '{keyword}'")
        return

    table = Table(
        title=f"[bold]{total_matches:,}[/bold] [dim]matches for[/dim] '{keyword}'",
        border_style="dim",
        show_lines=False,
    )
    table.add_column("age", style="dim", width=3, justify="right")
    table.add_column("bill_no", style="bold", width=9)
    table.add_column("date", width=10)
    table.add_column("committee", width=14)
    table.add_column("bill_name", max_width=50)
    table.add_column("proposer", style="dim", width=18)

    for _, r in results.iterrows():
        table.add_row(
            str(r["AGE"]),
            str(r["BILL_NO"]),
            str(r["PROPOSE_DT"])[:10],
            _truncate(r["COMMITTEE"], 14),
            _truncate(r["BILL_NAME"], 50),
            _truncate(r["PROPOSER"], 18),
        )
    console.print(table)

    if total_matches > limit:
        console.print(f"[dim]showing {limit} of {total_matches:,} -- use -n to see more[/dim]")


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("bill_id_or_no")
def show(bill_id_or_no: str):
    """Show full details of a single bill.

    \b
    Examples:
      assembly-bills show 2124567
      assembly-bills show PRC_R2A0X0T5I2I2R1I4B5A6P3G2S7W8P0
    """
    bills = load_bills()

    if bill_id_or_no.startswith("PRC_"):
        row = bills[bills["BILL_ID"] == bill_id_or_no]
    else:
        row = bills[bills["BILL_NO"].astype(str) == bill_id_or_no]

    if row.empty:
        console.print(f"[dim]bill not found:[/dim] {bill_id_or_no}")
        return

    row = row.iloc[0]
    bill_id = row["BILL_ID"]

    meta = (
        f"[dim]bill_id[/dim]     {bill_id}\n"
        f"[dim]bill_no[/dim]     {row['BILL_NO']}\n"
        f"[dim]name[/dim]        {row['BILL_NAME']}\n"
        f"[dim]assembly[/dim]    {row['AGE']}th\n"
        f"[dim]date[/dim]        {row['PROPOSE_DT']}\n"
        f"[dim]committee[/dim]   {row['COMMITTEE']}\n"
        f"[dim]proposer[/dim]    {row['PROPOSER']}\n"
        f"[dim]result[/dim]      {row['PROC_RESULT']}"
    )
    console.print(Panel(meta, border_style="dim", padding=(1, 2)))

    # Propose reason
    texts = load_texts()
    text_row = texts[texts["BILL_ID"] == bill_id]
    if not text_row.empty and pd.notna(text_row.iloc[0]["propose_reason"]):
        reason = text_row.iloc[0]["propose_reason"]
        wrapped = "\n".join(textwrap.wrap(reason, width=88))
        console.print(Panel(
            wrapped,
            title="[bold]propose reason[/bold]",
            title_align="left",
            border_style="dim",
            padding=(1, 2),
        ))
    else:
        console.print("[dim]no propose-reason text available[/dim]")

    # Proposers
    prop = load_proposers(columns=["BILL_ID", "PPSR_NM", "PPSR_POLY_NM", "REP_DIV"])
    bill_prop = prop[prop["BILL_ID"] == bill_id]
    if not bill_prop.empty:
        lead = bill_prop[bill_prop["REP_DIV"].notna()]
        cospon = bill_prop[bill_prop["REP_DIV"].isna()]
        lead_names = ", ".join(
            f"[bold]{r['PPSR_NM']}[/bold] [dim]({r['PPSR_POLY_NM']})[/dim]"
            for _, r in lead.iterrows()
        )
        cospon_names = ", ".join(cospon["PPSR_NM"].tolist())
        console.print(f"\n  [dim]lead[/dim]         {lead_names}")
        console.print(f"  [dim]co-sponsors[/dim]  {len(cospon)} members")
        if cospon_names:
            console.print(f"  [dim]names[/dim]        {_truncate(cospon_names, 200)}")
        console.print()


# ---------------------------------------------------------------------------
# mp
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("name")
@click.option("--age", type=int, help="Filter by assembly")
def mp(name: str, age: Optional[int]):
    """Look up an MP and their bills.

    \b
    Examples:
      assembly-bills mp "이재명"
      assembly-bills mp "한동훈" --age 22
    """
    mp_df = load_mp_metadata()
    mask = mp_df["HG_NM"].str.contains(name, case=False, na=False)
    if age:
        mask = mask & (mp_df["_age"].astype(str) == str(age))
    matches = mp_df[mask]

    if matches.empty:
        console.print(f"[dim]no MP found:[/dim] '{name}'")
        return

    for _, m in matches.iterrows():
        party = m.get("POLY_NM") or m.get("PLPT_NM", "")
        district = m.get("ORIG_NM") or m.get("ELECD_NM", "")
        seniority = m.get("REELE_GBN_NM") or m.get("RLCT_DIV_NM", "")
        cmit = m.get("CMIT_NM") or m.get("BLNG_CMIT_NM", "")

        info_text = (
            f"[dim]name[/dim]        [bold]{m['HG_NM']}[/bold] ({m.get('ENG_NM', '')})\n"
            f"[dim]assembly[/dim]    {m['_age']}\n"
            f"[dim]party[/dim]       {party}\n"
            f"[dim]district[/dim]    {district}\n"
            f"[dim]seniority[/dim]   {seniority}\n"
            f"[dim]committee[/dim]   {cmit}"
        )
        console.print(Panel(info_text, border_style="dim", padding=(1, 2)))

    # Bills where this MP is lead proposer
    prop = load_proposers(columns=["BILL_ID", "PPSR_NM", "REP_DIV"])
    lead_bills = prop[(prop["PPSR_NM"] == name) & (prop["REP_DIV"].notna())]

    if not lead_bills.empty:
        bills = load_bills(columns=["BILL_ID", "BILL_NO", "BILL_NAME", "AGE", "PROPOSE_DT"])
        led = bills[bills["BILL_ID"].isin(lead_bills["BILL_ID"])].sort_values(
            "PROPOSE_DT", ascending=False
        )

        table = Table(
            title=f"[bold]{len(led):,}[/bold] [dim]bills led by[/dim] {name}",
            border_style="dim",
        )
        table.add_column("age", style="dim", width=3, justify="right")
        table.add_column("bill_no", style="bold", width=9)
        table.add_column("date", width=10)
        table.add_column("bill_name", max_width=60)

        for _, r in led.head(20).iterrows():
            table.add_row(
                str(r["AGE"]), str(r["BILL_NO"]),
                str(r["PROPOSE_DT"])[:10], _truncate(r["BILL_NAME"], 60),
            )
        console.print(table)
        if len(led) > 20:
            console.print(f"[dim]... and {len(led) - 20} more[/dim]")


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--by", type=click.Choice(["year", "committee", "party", "age"]),
              default="year", help="Group by dimension")
def stats(by: str):
    """Show bill count statistics.

    \b
    Examples:
      assembly-bills stats
      assembly-bills stats --by party
      assembly-bills stats --by committee
    """
    bills = load_bills()

    if by == "year":
        bills["year"] = pd.to_datetime(bills["PROPOSE_DT"]).dt.year
        grouped = bills.groupby("year").size()
        title = "bills by year"
        col_name = "year"
    elif by == "committee":
        grouped = bills.groupby("COMMITTEE").size().sort_values(ascending=False).head(20)
        title = "bills by committee (top 20)"
        col_name = "committee"
    elif by == "party":
        prop = load_proposers(columns=["BILL_ID", "PPSR_POLY_NM", "REP_DIV"])
        lead = prop[prop["REP_DIV"].notna()].drop_duplicates("BILL_ID")
        grouped = lead["PPSR_POLY_NM"].value_counts().head(15)
        title = "bills by lead proposer party (top 15)"
        col_name = "party"
    else:  # age
        grouped = bills.groupby("AGE").size()
        title = "bills by assembly"
        col_name = "assembly"

    table = Table(title=title, border_style="dim")
    table.add_column(col_name, style="bold", min_width=16)
    table.add_column("count", style="dim", justify="right", width=8)
    table.add_column("", width=40)

    max_val = grouped.max()
    for label, count in grouped.items():
        bar_len = int(count / max_val * 40)
        bar = Text("█" * bar_len, style="blue")
        table.add_row(str(label), f"{count:,}", bar)

    console.print(table)


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("output_path")
@click.option("--keyword", help="Filter by keyword in bill name")
@click.option("--age", type=int, help="Filter by assembly")
@click.option("--with-text", is_flag=True, help="Include propose-reason text")
@click.option("--format", "fmt", type=click.Choice(["csv", "parquet"]), default="csv")
def export(output_path: str, keyword: Optional[str], age: Optional[int],
           with_text: bool, fmt: str):
    """Export filtered bills to CSV or Parquet.

    \b
    Examples:
      assembly-bills export ai_bills.csv --keyword "인공지능" --with-text
      assembly-bills export all_21.parquet --age 21 --format parquet
    """
    bills = load_bills()
    mask = pd.Series(True, index=bills.index)

    if keyword:
        mask = mask & bills["BILL_NAME"].str.contains(keyword, case=False, na=False)
    if age:
        mask = mask & (bills["AGE"] == age)

    result = bills[mask].copy()

    if with_text:
        texts = load_texts(columns=["BILL_ID", "propose_reason"])
        result = result.merge(texts, on="BILL_ID", how="left")

    if fmt == "csv":
        result.to_csv(output_path, index=False)
    else:
        result.to_parquet(output_path, index=False)

    console.print(f"[dim]exported[/dim] [bold]{len(result):,}[/bold] [dim]bills to[/dim] {output_path}")


if __name__ == "__main__":
    cli()
