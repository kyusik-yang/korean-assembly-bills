"""Basic tests for korean-assembly-bills."""

import pandas as pd
import pytest
from click.testing import CliRunner

from korean_assembly_bills import load_bills, load_texts, load_proposers, load_mp_metadata
from korean_assembly_bills.cli import cli


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

class TestDataLoading:
    def test_load_bills(self):
        df = load_bills()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 60925
        assert "BILL_ID" in df.columns

    def test_load_texts(self):
        df = load_texts()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 60925
        assert "propose_reason" in df.columns

    def test_load_proposers(self):
        df = load_proposers()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 769773
        assert "NASS_CD" in df.columns

    def test_load_mp_metadata(self):
        df = load_mp_metadata()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 947
        assert "MONA_CD" in df.columns

    def test_load_bills_select_columns(self):
        df = load_bills(columns=["BILL_ID", "BILL_NAME"])
        assert list(df.columns) == ["BILL_ID", "BILL_NAME"]

    def test_bill_ids_match(self):
        bill_ids = set(load_bills(columns=["BILL_ID"])["BILL_ID"])
        text_ids = set(load_texts(columns=["BILL_ID"])["BILL_ID"])
        assert bill_ids == text_ids


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCLI:
    @pytest.fixture()
    def runner(self):
        return CliRunner()

    def test_info(self, runner):
        result = runner.invoke(cli, ["info"])
        assert result.exit_code == 0
        assert "60" in result.output

    def test_search(self, runner):
        result = runner.invoke(cli, ["search", "인공지능"])
        assert result.exit_code == 0

    def test_search_no_results(self, runner):
        result = runner.invoke(cli, ["search", "xyznonexistent123"])
        assert result.exit_code == 0
        assert "no results" in result.output.lower()

    def test_stats(self, runner):
        result = runner.invoke(cli, ["stats"])
        assert result.exit_code == 0

    def test_show_not_found(self, runner):
        result = runner.invoke(cli, ["show", "0000000"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower()

    def test_mp_not_found(self, runner):
        result = runner.invoke(cli, ["mp", "xyznonexistent"])
        assert result.exit_code == 0
        assert "no mp found" in result.output.lower()
